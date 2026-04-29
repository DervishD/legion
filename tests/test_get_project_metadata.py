"""Test units for `get_project_metadata()` function."""
from copy import deepcopy
from hashlib import sha1
from pathlib import Path
import subprocess
import tomllib
from typing import TYPE_CHECKING

import pytest

from legion import (
    _git_repository_root,  # pyright: ignore[reportPrivateUsage]
    _load_pyproject,  # pyright: ignore[reportPrivateUsage]
    get_project_metadata,
)

from .helpers import CallableSpy

if TYPE_CHECKING:
    from typing import Any


TEST_PROJECT_ROOT = Path('/example/fake/project_root')
TEST_PROJECT_NAME = 'example_project'
TEST_PROJECT_VERSION = '0.42.73'
TEST_LOCAL_METADATA = {'local_key': 'local_value' }
TEST_PYPROJECT = {
    'project': {
        'name': TEST_PROJECT_NAME,
        'version': TEST_PROJECT_VERSION,
    },
    'example_key': 'example_value',
    'tool': {TEST_PROJECT_NAME: TEST_LOCAL_METADATA},
}
TEST_VERSION_METADATA = {
    'tag': TEST_PROJECT_VERSION,
    'distance': '137',
    'branch': 'example_branch',
    'detached': '',
    'rev': sha1(b'There was a button. I pushed it.', usedforsecurity=False).hexdigest(),
    'dirty': '.dirty',
}


def mock_git_repository_root(*_: object) -> Path:
    """Mock `_git_repository_root()`."""
    return TEST_PROJECT_ROOT

def mock_load_pyproject(*_: object) -> dict[str, Any]:
    """Mock `_load_pyproject()`."""
    return deepcopy(TEST_PYPROJECT)

def mock_load_pyproject_no_local(*_: object) -> dict[str, Any]:
    """Mock `_load_pyproject()` without a `tool` subtable."""
    metadata = deepcopy(TEST_PYPROJECT)
    del metadata['tool']
    return metadata

def mock_get_version_metadata(*_: object) -> dict[str, str]:
    """Mock `get_version_metadata()`."""
    return deepcopy(TEST_VERSION_METADATA)

def return_none(*_: object) -> None:
    """Monkeypatch helper to return `None`."""


@pytest.mark.parametrize(('returncode', 'stdout' , 'expected'), [
    pytest.param(0, 'example_repo', Path('example_repo').resolve(), id='test_git_repository_root_baseline'),
    pytest.param(0, 'example_repo\n\n', Path('example_repo').resolve(), id='test_git_repository_root_newlines'),
    pytest.param(1, '', None, id='test_git_repository_root_not_found'),
])
# pylint: disable-next=unused-variable
def test__git_repository_root(
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    expected: Path | None,
) -> None:
    """Test `_git_repository_root()` helper."""
    def _mock_run(*_a: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess('', returncode, stdout)
    mock_run_spy = CallableSpy(_mock_run)
    monkeypatch.setattr('legion.run', mock_run_spy)

    result = _git_repository_root()

    assert result == expected
    assert mock_run_spy.called
    assert mock_run_spy.call_count == 1


# pylint: disable-next=unused-variable
def test__load_pyproject_baseline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test `load_pyproject()` baseline."""
    monkeypatch.setattr('legion._git_repository_root', lambda: tmp_path)

    pyproject_path = tmp_path / 'pyproject.toml'
    pyproject_path.write_text('[project]\nname = "example_project"\nversion = "42.73.137"\n', encoding='utf-8')

    result = _load_pyproject(tmp_path)

    pyproject_path.unlink()

    assert result == {'project': {'name': 'example_project', 'version': '42.73.137'}}


# pylint: disable-next=unused-variable
def test__load_pyproject_not_found(tmp_path: Path) -> None:
    """Test `load_pyproject()` when the file does not exist."""
    assert _load_pyproject(tmp_path) is None


# pylint: disable-next=unused-variable
def test__load_pyproject_permission_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test `load_pyproject()` when the file cannot be read."""
    def mock_read_text(*_a: object, **_kw: object) -> None:
        raise PermissionError
    monkeypatch.setattr(Path, 'read_text', mock_read_text)
    (tmp_path / 'pyproject.toml').write_text('', encoding='utf-8')

    assert _load_pyproject(tmp_path) is None


# pylint: disable-next=unused-variable
def test__load_pyproject__invalid_toml(tmp_path: Path) -> None:
    """Test `load_pyproject()` when the file has invalid syntax."""
    (tmp_path / 'pyproject.toml').write_text('this is : not [ valid toml', encoding='utf-8')
    with pytest.raises(tomllib.TOMLDecodeError):
        _load_pyproject(tmp_path)


# pylint: disable-next=unused-variable
def test_get_project_metadata_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `get_project_metadata()` baseline."""
    expected: dict[str, Any] = deepcopy(TEST_PYPROJECT) | {
        'project_root': TEST_PROJECT_ROOT,
        'version': TEST_VERSION_METADATA,
        'local': TEST_LOCAL_METADATA,
    }
    expected['project']['version'] = TEST_PROJECT_VERSION
    monkeypatch.setattr('legion._git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion._load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.get_version_metadata', mock_get_version_metadata)

    project_metadata = get_project_metadata()
    assert project_metadata is not None
    assert project_metadata == expected

    monkeypatch.setattr('legion._load_pyproject', mock_load_pyproject_no_local)
    project_metadata = get_project_metadata()
    del expected['tool']
    expected['local'] = {}
    assert project_metadata is not None
    assert project_metadata == expected


# pylint: disable-next=unused-variable
def test_get_project_metadata_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that `None` is returned when it should."""
    monkeypatch.setattr('legion._git_repository_root', return_none)
    assert get_project_metadata() is None

    monkeypatch.setattr('legion._git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion._load_pyproject', return_none)
    assert get_project_metadata() is None

    monkeypatch.setattr('legion._load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.get_version_metadata', return_none)
    assert get_project_metadata() is None

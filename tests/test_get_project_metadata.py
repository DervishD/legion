"""Test units for `get_project_metadata()` function."""
from copy import deepcopy
from hashlib import sha1
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING

import pytest

from legion import _git_repository_root, get_project_metadata  # pyright: ignore[reportPrivateUsage]

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
    """Mock `git_repository_root()`."""
    return TEST_PROJECT_ROOT

def mock_load_pyproject(*_: object) -> dict[str, Any]:
    """Mock `load_pyproject()`."""
    return deepcopy(TEST_PYPROJECT)

def mock_load_pyproject_no_local(*_: object) -> dict[str, Any]:
    """Mock `load_pyproject()` without a `tool` subtable."""
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
def test_get_project_metadata_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `get_project_metadata()` baseline."""
    expected: dict[str, Any] = deepcopy(TEST_PYPROJECT) | {
        'project_root': TEST_PROJECT_ROOT,
        'version': TEST_VERSION_METADATA,
        'local': TEST_LOCAL_METADATA,
    }
    expected['project']['version'] = TEST_PROJECT_VERSION
    monkeypatch.setattr('legion._git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.get_version_metadata', mock_get_version_metadata)

    project_metadata = get_project_metadata()
    assert project_metadata is not None
    assert project_metadata == expected

    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject_no_local)
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
    monkeypatch.setattr('legion.load_pyproject', return_none)
    assert get_project_metadata() is None

    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.get_version_metadata', return_none)
    assert get_project_metadata() is None

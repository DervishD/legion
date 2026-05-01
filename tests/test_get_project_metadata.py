"""Test units for `get_project_metadata()` function and helpers."""
from copy import deepcopy
from hashlib import sha1
from pathlib import Path
import subprocess
import tomllib
from typing import TYPE_CHECKING

import pytest

from legion import (
    _get_version_metadata,  # pyright: ignore[reportPrivateUsage]
    _git_repository_root,  # pyright: ignore[reportPrivateUsage]
    _load_pyproject,  # pyright: ignore[reportPrivateUsage]
    _resolve_metadata,  # pyright: ignore[reportPrivateUsage]
    get_project_metadata,
)

from .helpers import CallableSpy

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any




########################################################################
#                                                                      #
#   Test units for _git_repository_root()                              #
#                                                                      #
########################################################################




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
    def mock_run(*_a: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess('', returncode, stdout)
    mock_run_spy = CallableSpy(mock_run)
    monkeypatch.setattr('legion.run', mock_run_spy)

    result = _git_repository_root()

    assert result == expected
    assert mock_run_spy.called
    assert mock_run_spy.call_count == 1




########################################################################
#                                                                      #
#   Test units for _load_pyproject()                                   #
#                                                                      #
########################################################################




# pylint: disable-next=unused-variable
def test__load_pyproject_baseline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test `_load_pyproject()` baseline."""
    monkeypatch.setattr('legion._git_repository_root', lambda: tmp_path)

    pyproject_path = tmp_path / 'pyproject.toml'
    pyproject_path.write_text('[project]\nname = "example_project"\nversion = "42.73.137"\n', encoding='utf-8')

    result = _load_pyproject(tmp_path)

    pyproject_path.unlink()

    assert result == {'project': {'name': 'example_project', 'version': '42.73.137'}}


# pylint: disable-next=unused-variable
def test__load_pyproject_not_found(tmp_path: Path) -> None:
    """Test `_load_pyproject()` when the file does not exist."""
    assert _load_pyproject(tmp_path) is None


# pylint: disable-next=unused-variable
def test__load_pyproject_permission_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test `_load_pyproject()` when the file cannot be read."""
    def mock_read_text(*_a: object, **_kw: object) -> None:
        raise PermissionError
    monkeypatch.setattr(Path, 'read_text', mock_read_text)
    (tmp_path / 'pyproject.toml').write_text('', encoding='utf-8')

    assert _load_pyproject(tmp_path) is None


# pylint: disable-next=unused-variable
def test__load_pyproject__invalid_toml(tmp_path: Path) -> None:
    """Test `_load_pyproject()` when the file has invalid syntax."""
    (tmp_path / 'pyproject.toml').write_text('this is : not [ valid toml', encoding='utf-8')
    with pytest.raises(tomllib.TOMLDecodeError):
        _load_pyproject(tmp_path)




########################################################################
#                                                                      #
#   Test units for _get_version_metadata()                             #
#                                                                      #
########################################################################




class MockCompletedProcess:
    """Mock implementation of `subprocess.CompletedProcess`."""  # noqa: D204
    def __init__(self, returncode: int, stdout: str) -> None:
        """."""
        self.returncode = returncode
        self.stdout = stdout


def mock_run_factory(results: list[MockCompletedProcess]) -> Callable[..., MockCompletedProcess]:
    """Produce `legion.run()` replacements.

    Return a closure that returns the next result of the *results* queue
    on every invocation.
    """
    queue = iter(results)
    def wrapped(*_a: object, **_kw: object) -> MockCompletedProcess:
        return next(queue)
    return wrapped


TAG = '0.42.73'
RELEASE = '42.37'
DISTANCE = '137'
BRANCH = 'main'
DETACHED = 'detached'
REV = sha1(b'There was a button. I pushed it.', usedforsecurity=False).hexdigest()
DIRTY = '.dirty'

CLEAN_WORKTREE = f'v{TAG}-{DISTANCE}-g{REV}\n'
CLEAN_NOT_V_NOR_G = f'{TAG}-{DISTANCE}-{REV}\n'
DIRTY_WORKTREE = f'v{TAG}-{DISTANCE}-g{REV}-{DIRTY.lstrip('.')}\n'

VERSION_METADATA_KEYS = ('tag', 'distance', 'branch', 'detached', 'rev', 'dirty')
def build_test_version_metadata_dict(*values: str) -> dict[str, str]:
    """Return a metadata dictionary from *values*."""
    return dict(zip(VERSION_METADATA_KEYS, values, strict=True)) | {'release': ''}


@pytest.mark.parametrize(('changelog_contents', 'expected'), [
    pytest.param(f'## [{RELEASE}] 2084-07-07 06:54:54.9', RELEASE, id='test__get_version_metadata_changelog_baseline'),
    pytest.param('## []', '', id='test__get_version_metadata_changelog_no_match'),
    pytest.param('', '', id='test__get_version_metadata_changelog_empty'),
])
# pylint: disable-next=unused-variable
def test__get_version_metadata_changelog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    changelog_contents: str,
    expected: str,
) -> None:
    """Test `_get_version_metadata()` functionality, changelog mode."""
    changelog = tmp_path / 'example_CHANGELOG.md'
    changelog.write_text(changelog_contents, encoding='utf-8')
    monkeypatch.setattr('legion.run', mock_run_factory([
        MockCompletedProcess(0, CLEAN_WORKTREE),
        MockCompletedProcess(0, BRANCH),
    ]))

    result = _get_version_metadata(changelog)
    changelog.unlink()

    assert result is not None
    assert result == build_test_version_metadata_dict(TAG, DISTANCE, BRANCH, '', REV, '') | {'release': expected}


# pylint: disable-next=unused-variable
def test__get_version_metadata_changelog_no_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test `_get_version_metadata()` with no release data."""
    expected = build_test_version_metadata_dict(TAG, DISTANCE, BRANCH, '', REV, '')

    monkeypatch.setattr('legion.run', mock_run_factory([
        MockCompletedProcess(0, CLEAN_WORKTREE),
        MockCompletedProcess(0, BRANCH),
    ]))
    result = _get_version_metadata(tmp_path / 'non_existent')
    assert result is not None
    assert result == expected

    def mock_read_text(*_a: object, **_kw: object) -> None:
        raise PermissionError
    monkeypatch.setattr(Path, 'read_text', mock_read_text)
    monkeypatch.setattr('legion.run', mock_run_factory([
        MockCompletedProcess(0, CLEAN_WORKTREE),
        MockCompletedProcess(0, BRANCH),
    ]))
    result = _get_version_metadata(tmp_path / 'non_readable')
    assert result is not None
    assert result == expected


@pytest.mark.parametrize(('results', 'expected'), [
    pytest.param(
        [MockCompletedProcess(1, '')],
        None,
        id='test_resolve_version_git_no_metadata',
    ),
    pytest.param(
        [MockCompletedProcess(0, CLEAN_WORKTREE), MockCompletedProcess(0, BRANCH)],
        build_test_version_metadata_dict(TAG, DISTANCE, BRANCH, '', REV, ''),
        id='test_resolve_version_git_baseline_clean',
    ),
    pytest.param(
        [MockCompletedProcess(0, DIRTY_WORKTREE), MockCompletedProcess(0, BRANCH)],
        build_test_version_metadata_dict(TAG, DISTANCE, BRANCH, '', REV, DIRTY),
        id='test_resolve_version_git_baseline_dirty',
    ),
    pytest.param(
        [MockCompletedProcess(0, CLEAN_NOT_V_NOR_G), MockCompletedProcess(0, BRANCH)],
        build_test_version_metadata_dict(TAG, DISTANCE, BRANCH, '', REV, ''),
        id='test_resolve_version_git_no_v_nor_g',
    ),
    pytest.param(
        [MockCompletedProcess(0, CLEAN_WORKTREE), MockCompletedProcess(1, '')],
        build_test_version_metadata_dict(TAG, DISTANCE, '', DETACHED, REV, ''),
        id='test_resolve_version_git_detached_head',
    ),
    pytest.param(
        [MockCompletedProcess(0, CLEAN_WORKTREE), MockCompletedProcess(0, f'branch with,{BRANCH}/extra-separators')],
        build_test_version_metadata_dict(TAG, DISTANCE, f'branchxxxwithxxx{BRANCH}xxxextraxxxseparators', '', REV, ''),
        id='test_resolve_version_git_sanitize_branch',
    ),
])
# pylint: disable-next=unused-variable
def test__get_version_metadata_git(
    monkeypatch: pytest.MonkeyPatch,
    results: list[MockCompletedProcess],
    expected: dict[str, str],
) -> None:
    """Test `_get_version_metadata()` functionality, git mode."""
    monkeypatch.setattr('legion.run', mock_run_factory(results))

    version_metadata = _get_version_metadata()
    assert version_metadata == expected




########################################################################
#                                                                      #
#   Test units for _resolve_metadata()                                 #
#                                                                      #
########################################################################




EVAL_PREFIX = '!!'

@pytest.fixture
# pylint: disable-next=unused-variable
def metadata() -> dict[str, Any]:
    """Return a fresh copy of the sample metadata."""
    return {
        'toplevel_string': 'There was a button. I pushed it.',
        'toplevel_dict': {'example_key': 'example_value'},
        'local': {
            'string': 'example_string',
            'int': 42,
            'float': 73.137,
            'bool': False,
            'eval': f'{EVAL_PREFIX}len({{local[string]!r}})',
            'eval_type_preserve': f'{EVAL_PREFIX}[42, 73, 137]',
            'simple_interpolation': '{local[eval]}/{toplevel_string}',
            'chained_interpolation': '{local[simple_interpolation]}/{toplevel_dict[example_key]}',
            'list': [
                42,
                'example_string_in_list',
                {'int_in_dict_in_list': 42, 'string_in_dict_in_list': 'example_string_in_dict_in_list'},
            ],
            'dict': {
                'int_in_dict': 42,
                'string_in_dict': 'example_string_in_dict',
                'list_in_dict': [42, 'examples_string_in_list_in_dict'],
            },
            'empty_list': [],
            'empty_dict': {},
        },
    }


EXPECTED = {
    'toplevel_string': 'There was a button. I pushed it.',
    'toplevel_dict': {'example_key': 'example_value'},
    'local': {
        'string': 'example_string',
        'int': 42,
        'float': 73.137,
        'bool': False,
        'eval': 14,
        'eval_type_preserve': [42, 73, 137],
        'simple_interpolation': '14/There was a button. I pushed it.',
        'chained_interpolation': '14/There was a button. I pushed it./example_value',
        'list': [
            42,
            'example_string_in_list',
            {'int_in_dict_in_list': 42, 'string_in_dict_in_list': 'example_string_in_dict_in_list'},
        ],
        'dict': {
            'int_in_dict': 42,
            'string_in_dict': 'example_string_in_dict',
            'list_in_dict': [42, 'examples_string_in_list_in_dict'],
        },
        'empty_list': [],
        'empty_dict': {},
    },
}


# pylint: disable-next=unused-variable,redefined-outer-name
def test__resolve_metadata_baseline(metadata: dict[str, Any]) -> None:
    """Test `_resolve_metadata()` baseline."""
    original = deepcopy(metadata)
    resolved = _resolve_metadata(metadata, EVAL_PREFIX)
    assert metadata == original
    assert resolved == EXPECTED


# pylint: disable-next=unused-variable,redefined-outer-name
def test__resolve_metadata_unresolvable_placeholder(metadata: dict[str, Any]) -> None:
    """Test that unresolvable placeholders raise `KeyError`."""
    metadata['local']['dict']['unresolvable'] = '{unresolvable[placeholder]}'
    with pytest.raises(KeyError):
        _resolve_metadata(metadata, EVAL_PREFIX)




########################################################################
#                                                                      #
#   Test units for get_project_metadata()                              #
#                                                                      #
########################################################################




TEST_PROJECT_ROOT = Path('/example/fake/project_root')
TEST_PROJECT_NAME = 'example_project'
TEST_PROJECT_RELEASE = '1.42.73'
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
    'release': TEST_PROJECT_RELEASE,
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
    metadata_no_tool = deepcopy(TEST_PYPROJECT)
    del metadata_no_tool['tool']
    return metadata_no_tool
def mock_get_version_metadata(*_: object) -> dict[str, str]:
    """Mock `get_version_metadata()`."""
    return deepcopy(TEST_VERSION_METADATA)
def return_none(*_: object) -> None:
    """Monkeypatch helper to return `None`."""


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
    monkeypatch.setattr('legion._get_version_metadata', mock_get_version_metadata)

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
    monkeypatch.setattr('legion._get_version_metadata', return_none)
    assert get_project_metadata() is None

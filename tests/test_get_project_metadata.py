"""Test units for `get_project_metadata()` function."""
from copy import deepcopy
from hashlib import sha1
from pathlib import Path
from typing import TYPE_CHECKING

from legion import get_project_metadata

if TYPE_CHECKING:
    from typing import Any

    import pytest


MOCK_PROJECT_NAME = 'mock_project'
MOCK_PROJECT_VERSION = '0.42.73'
MOCK_PYPROJECT = {
    'project': {
        'name': MOCK_PROJECT_NAME,
        'version': MOCK_PROJECT_VERSION,
    },
    'mock_key': 'mock_value',
}
MOCK_PROJECT_ROOT = Path('/mock/project_root')
MOCK_VERSION_METADATA = {
    'tag': MOCK_PROJECT_VERSION,
    'distance': '137',
    'branch': 'mock_branch',
    'detached': '',
    'rev': sha1(b'There was a button. I pushed it.', usedforsecurity=False).hexdigest(),
    'dirty': '.dirty',
}
MOCK_TIMESTAMP = '2084-07-07 06:54:54.9'  # TMA-1


def mock_git_repository_root(*_: object) -> Path:
    """Mock `git_repository_root()`."""
    return MOCK_PROJECT_ROOT

def mock_load_pyproject(*_: object) -> dict[str, Any]:
    """Mock `load_pyproject()`."""
    return deepcopy(MOCK_PYPROJECT)

def mock_get_version_metadata(*_: object) -> dict[str, str]:
    """Mock `get_version_metadata()`."""
    return deepcopy(MOCK_VERSION_METADATA)

def mock_timestamp(*_: object) -> str:
    """Mock `timestamp()`."""
    return MOCK_TIMESTAMP

def return_none(*_: object) -> None:
    """Monkeypatch helper to return `None`."""


# pylint: disable-next=unused-variable
def test_get_project_metadata_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `get_project_metadata()` baseline."""
    expected: dict[str, Any] = deepcopy(MOCK_PYPROJECT) | {
        'project_root': MOCK_PROJECT_ROOT,
        'version': MOCK_VERSION_METADATA,
        'timestamp': MOCK_TIMESTAMP,
    }
    expected['project']['version'] = MOCK_PROJECT_VERSION
    monkeypatch.setattr('legion.git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.get_version_metadata', mock_get_version_metadata)
    monkeypatch.setattr('legion.timestamp', mock_timestamp)

    project_metadata = get_project_metadata()
    assert project_metadata is not None
    assert project_metadata == expected


# pylint: disable-next=unused-variable
def test_get_project_metadata_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that `None` is returned when it should."""
    monkeypatch.setattr('legion.git_repository_root', return_none)
    assert get_project_metadata() is None

    monkeypatch.setattr('legion.git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion.load_pyproject', return_none)
    assert get_project_metadata() is None

    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.get_version_metadata', return_none)
    assert get_project_metadata() is None

"""Test units for `get_version_metadata()` function."""
from hashlib import sha1
from typing import TYPE_CHECKING

import pytest

from legion import get_version_metadata

if TYPE_CHECKING:
    from collections.abc import Callable


class MockCompletedProcess:
    """Mock implementation of `subprocess.CompletedProcess`."""  # noqa: D204
    def __init__(self, returncode: int, stdout: str) -> None:
        """."""
        self.returncode = returncode
        self.stdout = stdout


def mock_run(results: list[MockCompletedProcess]) -> Callable[..., MockCompletedProcess]:
    """Produce `legion.run()` replacements.

    Return a closure that returns the next result of the *results* queue
    on every invocation.
    """
    queue = iter(results)
    def wrapped(*_a: object, **_kw: object) -> MockCompletedProcess:
        return next(queue)
    return wrapped


VERSION_METADATA_KEYS = ('tag', 'distance', 'branch', 'detached', 'rev', 'dirty')
def mock_metadata_dict(*values: str) -> dict[str, str]:
    """Return a metadata dictionary from *values*."""
    return dict(zip(VERSION_METADATA_KEYS, values, strict=True))


TAG = '0.42.73'
DISTANCE = '137'
BRANCH = 'main'
DETACHED = 'detached'
REV = sha1(b'There was a button. I pushed it.', usedforsecurity=False).hexdigest()
DIRTY = '.dirty'

CLEAN_WORKTREE = f'v{TAG}-{DISTANCE}-g{REV}\n'
CLEAN_NOT_V_NOR_G = f'{TAG}-{DISTANCE}-{REV}\n'
DIRTY_WORKTREE = f'v{TAG}-{DISTANCE}-g{REV}-{DIRTY.lstrip('.')}\n'

@pytest.mark.parametrize(('results', 'expected'), [
    pytest.param(
        [MockCompletedProcess(1, '')],
        None,
        id='test_resolve_version_no_metadata',
    ),
    pytest.param(
        [MockCompletedProcess(0, CLEAN_WORKTREE), MockCompletedProcess(0, BRANCH)],
        mock_metadata_dict(TAG, DISTANCE, BRANCH, '', REV, ''),
        id='test_resolve_version_baseline_clean',
    ),
    pytest.param(
        [MockCompletedProcess(0, DIRTY_WORKTREE), MockCompletedProcess(0, BRANCH)],
        mock_metadata_dict(TAG, DISTANCE, BRANCH, '', REV, DIRTY),
        id='test_resolve_version_baseline_dirty',
    ),
    pytest.param(
        [MockCompletedProcess(0, CLEAN_NOT_V_NOR_G), MockCompletedProcess(0, BRANCH)],
        mock_metadata_dict(TAG, DISTANCE, BRANCH, '', REV, ''),
        id='test_resolve_version_no_v_nor_g',
    ),
    pytest.param(
        [MockCompletedProcess(0, CLEAN_WORKTREE), MockCompletedProcess(1, '')],
        mock_metadata_dict(TAG, DISTANCE, '', DETACHED, REV, ''),
        id='test_resolve_version_detached_head',
    ),
    pytest.param(
        [MockCompletedProcess(0, CLEAN_WORKTREE), MockCompletedProcess(0, f'branch with,{BRANCH}/extra-separators')],
        mock_metadata_dict(TAG, DISTANCE, f'branchxxxwithxxx{BRANCH}xxxextraxxxseparators', '', REV, ''),
        id='test_resolve_version_sanitize_branch',
    ),
])
# pylint: disable-next=unused-variable
def test_get_version_metadata(
    monkeypatch: pytest.MonkeyPatch,
    results: list[MockCompletedProcess],
    expected: dict[str, str],
) -> None:
    """Test `get_version_metadata()` functionality."""
    monkeypatch.setattr('legion.run', mock_run(results))

    version_metadata = get_version_metadata()
    assert version_metadata == expected

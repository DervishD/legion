"""Test units for `resolve_version()` function."""
from hashlib import sha1
from typing import TYPE_CHECKING

import pytest

from legion import resolve_version

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


TAG = '0.42.73'
DISTANCE = '137'
REV = sha1(b'There was a button. I pushed it.', usedforsecurity=False).hexdigest()
MAIN_BRANCH = 'main'
DETACHED_HEAD = 'detached'
DIRTY_MARKER = '.dirty'

CLEAN = f'v{TAG}-{DISTANCE}-g{REV}\n'
DIRTY = f'v{TAG}-{DISTANCE}-g{REV}-{DIRTY_MARKER.lstrip('.')}\n'

@pytest.mark.parametrize(('template', 'results', 'expected'), [
    pytest.param(
        None,
        [MockCompletedProcess(1, '')],
        None,
        id='test_resolve_version_no_metadata',
    ),
    pytest.param(
        None,
        [MockCompletedProcess(0, CLEAN), MockCompletedProcess(0, MAIN_BRANCH)],
        f'{TAG}.post{DISTANCE}+{MAIN_BRANCH}.{REV}',
        id='test_resolve_version_baseline_clean',
    ),
    pytest.param(
        None,
        [MockCompletedProcess(0, DIRTY), MockCompletedProcess(0, MAIN_BRANCH)],
        f'{TAG}.post{DISTANCE}+{MAIN_BRANCH}.{REV}{DIRTY_MARKER}',
        id='test_resolve_version_baseline_dirty',
    ),
    pytest.param(
        '{tag}+{rev}',
        [MockCompletedProcess(0, f'{TAG}-{DISTANCE}-{REV}'), MockCompletedProcess(1, '')],
        f'{TAG}+{REV}',
        id='test_resolve_version_no_v_or_g',
    ),
    pytest.param(
        '{branch}{detached}',
        [MockCompletedProcess(0, CLEAN), MockCompletedProcess(1, '')],
        f'{DETACHED_HEAD}',
        id='test_resolve_version_detached_head',
    ),
    pytest.param(
        '{branch}{detached}',
        [MockCompletedProcess(0, CLEAN), MockCompletedProcess(0, MAIN_BRANCH)],
        f'{MAIN_BRANCH}',
        id='test_resolve_version_non_detached_head',
    ),
    pytest.param(
        '{branch}',
        [MockCompletedProcess(0, CLEAN), MockCompletedProcess(0, f'branch with,{MAIN_BRANCH}/extra-separators')],
        f'branchxxxwithxxx{MAIN_BRANCH}xxxextraxxxseparators',
        id='test_resolve_version_sanitize_branch',
    ),
    pytest.param(
        'D{dirty}D/r{rev}&ver{tag}({distance})[{detached}.{branch}]',
        [ MockCompletedProcess(0, CLEAN), MockCompletedProcess(0, MAIN_BRANCH)],
        f'DD/r{REV}&ver{TAG}({DISTANCE})[.{MAIN_BRANCH}]',
        id='test_resolve_version_custom_template',
    ),
])
# pylint: disable-next=unused-variable
def test_resolve_version(
    monkeypatch: pytest.MonkeyPatch,
    template: str | None,
    results: list[MockCompletedProcess],
    expected: str,
) -> None:
    """Test `resolve_metadata()` functionality."""
    monkeypatch.setattr('legion.run', mock_run(results))

    resolved_version = resolve_version() if template is None else resolve_version(template)
    assert resolved_version == expected


# pylint: disable-next=unused-variable
def test_resolve_version_key_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `resolve_version()` raises `KeyError` when appropriate."""
    monkeypatch.setattr('legion.run', mock_run([MockCompletedProcess(0, CLEAN), MockCompletedProcess(1, '')]))

    with pytest.raises(KeyError) as excinfo:
        resolve_version('{unknown}')

    assert isinstance(excinfo.value, KeyError)
    assert excinfo.value.args == ('unknown',)

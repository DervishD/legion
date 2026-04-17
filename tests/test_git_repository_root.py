"""Test units for `git_repository_root()` function."""
from pathlib import Path
import subprocess

import pytest

from legion import git_repository_root
from tests.helpers import CallableSpy


@pytest.mark.parametrize(('cwd', 'returncode', 'stdout' , 'expected'), [
    pytest.param(None, 0, 'mock_repo', Path('mock_repo').resolve(), id='test_git_repository_root_baseline'),
    pytest.param(Path('mock_cwd'), 0, 'mock_repo', Path('mock_repo').resolve(), id='test_git_repository_root_cwd'),
    pytest.param(None, 0, 'mock_repo\n\n', Path('mock_repo').resolve(), id='test_git_repository_root_newlines'),
    pytest.param(None, 1, '', None, id='test_git_repository_root_not_found'),
])
# pylint: disable-next=unused-variable
def test_git_repository_root(
    monkeypatch: pytest.MonkeyPatch,
    cwd: Path | None,
    returncode: int,
    stdout: str,
    expected: Path | None,
) -> None:
    """Test `git_repository_root()`."""
    def _mock_run(*_a: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess('', returncode, stdout)
    mock_run_spy = CallableSpy(_mock_run)
    monkeypatch.setattr('legion.run', mock_run_spy)

    result = git_repository_root(cwd)

    assert result == expected
    assert mock_run_spy.called
    assert mock_run_spy.call_count == 1
    assert mock_run_spy.calls[0][2]['cwd'] == (cwd or Path()).resolve()

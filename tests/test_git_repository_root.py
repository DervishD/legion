"""Test units for `git_repository_root()` function."""
from pathlib import Path
import subprocess

import pytest

from legion import git_repository_root


@pytest.mark.parametrize(('returncode', 'stdout' , 'expected'), [
    pytest.param(0, 'mock_repo', Path('mock_repo').resolve(), id='test_git_repository_root_baseline'),
    pytest.param(0, 'mock_repo\n\n', Path('mock_repo').resolve(), id='test_git_repository_root_newlines'),
    pytest.param(1, '', None, id='test_git_repository_root_not_found'),
])
# pylint: disable-next=unused-variable
def test_git_repository_root(
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    expected: Path | None,
) -> None:
    """Test `git_repository_root()`."""
    def _mock_run(*_a: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess('', returncode, stdout)
    monkeypatch.setattr('legion.run', _mock_run)

    result = git_repository_root()

    assert result == expected

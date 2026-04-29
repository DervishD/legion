"""Test units for `run()` function."""
import subprocess
import sys

import pytest

from legion import run

from .helpers import CallableSpy


@pytest.mark.parametrize(('platform', 'input_kwargs', 'expected_kwargs'), [
    pytest.param(
        'win32',
        {},
        {
            'capture_output': True,
            'check': False,
            'text': True,
            'errors': 'replace',
            'creationflags': subprocess.CREATE_NO_WINDOW,
        },
        id='test_run_win32_baseline',
    ),
    pytest.param(
        'win32',
        {'creationflags': 42},
        {
            'capture_output': True,
            'check': False,
            'text': True,
            'errors': 'replace',
            'creationflags': 42,
        },
        id='test_run_win32_creationflags_modified',
    ),
    pytest.param(
        'any',
        {},
        {
            'capture_output': True,
            'check': False,
            'text': True,
            'errors': 'replace',
        },
        id='test_run_baseline',
    ),
    pytest.param(
        'any',
        {'capture_output': False},
        {
            'capture_output': False,
            'check': False,
        },
        id='test_run_capture_output_modified',
    ),
    pytest.param(
        'any',
        {'check': True},
        {
            'capture_output': True,
            'check': True,
            'text': True,
            'errors': 'replace',
        },
        id='test_run_check_modified',
    ),
    pytest.param(
        'any',
        {'text': False},
        {
            'capture_output': True,
            'check': False,
            'text': False,
            'errors': 'replace',
        },
        id='test_run_text_modified',
    ),
    pytest.param(
        'any',
        {'errors': 'strict'},
        {
            'capture_output': True,
            'check': False,
            'text': True,
            'errors': 'strict',
        },
        id='test_run_errors_modified',
    ),
])
# pylint: disable-next=unused-variable
def test_run(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    input_kwargs: dict[str, object],
    expected_kwargs: dict[str, object])-> None:
    """Test `run()` handling of input arguments."""
    retval: subprocess.CompletedProcess[str] = subprocess.CompletedProcess('', 0)
    def mock_subprocess_run(*_a: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return retval
    subprocess_run_spy = CallableSpy(mock_subprocess_run)
    monkeypatch.setattr(subprocess, 'run', subprocess_run_spy)
    monkeypatch.setattr(sys, 'platform', platform)

    command = ('example_command', 'example_argument')
    run(command, **input_kwargs)

    assert subprocess_run_spy.called
    assert subprocess_run_spy.call_count == 1
    assert subprocess_run_spy.calls[0] == (retval, (command,), expected_kwargs)

"""Test units for `excepthook()` function and helpers."""
import errno
from os import strerror
from random import choice, randint, sample
from string import ascii_lowercase
import sys
import traceback
from traceback import FrameSummary, StackSummary
from typing import TYPE_CHECKING

import pytest

# ruff: disable[SLF001]
# pylint: disable=protected-access
# pyright: reportPrivateUsage=false
import legion
from tests.helpers import CallableSpy, LoggingFields, parse_logfile

if TYPE_CHECKING:
    from types import TracebackType

    from tests.helpers import LoggingPaths


# pylint: disable-next=unused-variable
def test_excepthook_keyboard_interrupt_handling() -> None:
    """Test `KeyboardInterrupt` handling."""
    sys.__excepthook__ = CallableSpy(sys.__excepthook__)
    sys.excepthook = legion.excepthook

    exc = KeyboardInterrupt()
    args = (KeyboardInterrupt, exc, exc.__traceback__)
    legion.excepthook(KeyboardInterrupt, exc, exc.__traceback__)

    assert sys.__excepthook__.called
    assert sys.__excepthook__.calls[0][1] == args


@pytest.mark.parametrize(('exception', 'expected'), [
    pytest.param(
        OSError(errno.ENOENT, strerror(errno.ENOENT) + '...', 'mock_filename1.txt', errno.ENOENT, 'mock_filename2.txt'),
        (
            f'errcodes   ⟶  {errno.errorcode[errno.ENOENT]}/WinError{errno.ENOENT}\n'
            f'strerror   ⟶  {strerror(errno.ENOENT)}\n'
             'filename1  ⟶  mock_filename1.txt\n'
             'filename2  ⟶  mock_filename2.txt'
        ),
        id='test__format_exception_details_oserror_baseline',
    ),
    pytest.param(
        OSError(errno.ENOENT, None, 'mock_filename1.txt', errno.ENOENT),
        (
            f'errcodes   ⟶  {errno.errorcode[errno.ENOENT]}/WinError{errno.ENOENT}\n'
             'strerror   ⟶  ???\n'
             'filename1  ⟶  mock_filename1.txt\n'
             'filename2  ⟶  ???'
        ),
        id='test__format_exception_details_oserror_partial',
    ),
    pytest.param(
        OSError(),
        (
            'errcodes   ⟶  WinErrorNone\n'
            'strerror   ⟶  ???\n'
            'filename1  ⟶  ???\n'
            'filename2  ⟶  ???'
        ),
        id='test__format_exception_details_oserror_void',
    ),
    pytest.param(
        Exception('mock message', 42, 3.14, True),  # noqa: FBT003
        (
             'str    ⟶  mock message\n'
             'int    ⟶  42\n'
             'float  ⟶  3.14\n'
             'bool   ⟶  True'
        ),
        id='test__format_exception_details_exception',
    ),
    pytest.param(
        Exception(),
        '',
        id='test__format_exception_details_void',
    ),
    pytest.param(
        Exception(None),
        'NoneType  ⟶  ???',
        id='test__format_exception_details_none',
    ),
    pytest.param(
        Exception(''),
        'str  ⟶  ???',
        id='test__format_exception_details_empty',
    ),
    pytest.param(
        Exception(' ' * 42),
        'str  ⟶  ???',
        id='test__format_exception_details_whitespace',
    ),
    pytest.param(
        Exception('  stripped  '),
        'str  ⟶  stripped',
        id='test__format_exception_details_strip',
    ),
])
# pylint: disable-next=unused-variable
def test__format_exception_details(exception: Exception, expected: str) -> None:
    """Test `_format_exception_details()`."""
    assert legion._format_exception_details(exception) == expected


# pylint: disable-next=unused-variable
def test_excepthook_format_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `_format_traceback()`."""
    min_items = 3
    max_items = 9
    min_lineno = 1
    max_lineno = 999

    expected = ''
    mock_frames: list[FrameSummary] = []

    # ruff: disable[S311]
    for file_index in sample(ascii_lowercase, randint(min_items, max_items)):
        filename = f'source_file_{file_index}.py'
        expected += f'⟶ {filename}\n'
        for _j in range(randint(min_items, max_items)):
            location = (randint(min_lineno, max_lineno), f'func_{choice(ascii_lowercase)}')
            codeline = f'source_code_{choice(ascii_lowercase)}'
            mock_frames.append(FrameSummary(filename, *location, line=codeline))
            expected += '  {}, {}: {}\n'.format(*location, codeline)  # pylint: disable=consider-using-f-string
    # ruff: enable[S311]

    def mock_extract_tb (_: TracebackType) -> StackSummary:
        return StackSummary.from_list(mock_frames)

    monkeypatch.setattr(traceback, 'extract_tb', mock_extract_tb)

    assert legion._format_traceback(None) == expected.removesuffix('\n')


@pytest.mark.parametrize(('has_args', 'has_traceback'), [
    pytest.param(True, True, id='test_excepthook_formatting_full_output'),
    pytest.param(False, True, id='test_excepthook_formatting_no_details'),
    pytest.param(True, False, id='test_excepthook_formatting_no_traceback'),
    pytest.param(False, False, id='test_excepthook_formatting_no_output'),
])
@pytest.mark.usefixtures('logger')
# pylint: disable-next=unused-variable
def test_excepthook_formatting(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    logging_paths: LoggingPaths,
    has_args: bool,  # noqa: FBT001
    has_traceback: bool,  # noqa: FBT001
) -> None:
    """Test `excepthook` full formatting."""
    def patched_extract_tb(_: TracebackType) -> StackSummary:
        return StackSummary.from_list([FrameSummary('filename.py', 1, 'func', line='codeline')])

    monkeypatch.setattr(traceback, 'extract_tb', patched_extract_tb)

    exc = Exception(*((42,) if has_args else ()))
    legion.excepthook(type(exc), exc, exc.__traceback__ if has_traceback else None)

    heading = f'Unhandled exception ({type(exc).__name__})'
    formatted_details = [legion._format_exception_details(exc)]
    formatted_details.append(legion._format_traceback(exc.__traceback__))

    expected = legion.format_message(heading, '\n\n'.join(formatted_details)).split('\n')

    parsed_main_logfile = parse_logfile(logging_paths.main)
    parsed_full_logfile = parse_logfile(logging_paths.full)

    assert parsed_main_logfile[LoggingFields.MESSAGES] == expected
    assert parsed_full_logfile[LoggingFields.MESSAGES] == expected

    assert set(parsed_main_logfile[LoggingFields.LOGLEVELS]) == {''}
    assert set(parsed_full_logfile[LoggingFields.LOGLEVELS]) == {'ERROR'}

    captured = capsys.readouterr()

    assert not captured.out
    assert captured.err.splitlines() == expected

# ruff: enable[SLF001]  # pylint: enable=protected-access

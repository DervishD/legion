"""Test units for `excepthook()` function and helpers."""
import errno
from os import strerror
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


@pytest.mark.parametrize(('frames', 'expected'), [
    pytest.param(
        [],
        '',
        id='test__format_traceback_no_frames',
    ),
    pytest.param(
        [FrameSummary('mock_file.py', 42, 'mock_func', line='mock_line_of_code')],
        (
            '⟶ mock_file.py\n'
            '  42, mock_func: mock_line_of_code'
        ),
        id='test__format_traceback_single_frame',
    ),
    pytest.param(
        [FrameSummary('mock_file.py', None, 'mock_func', line='mock_line_of_code')],
        (
            '⟶ mock_file.py\n'
            '  1, mock_func: mock_line_of_code'
        ),
        id='test__format_traceback_none_lineno',
    ),
    pytest.param(
        [FrameSummary('mock_file.py', 0, 'mock_func', line='mock_line_of_code')],
        (
            '⟶ mock_file.py\n'
            '  1, mock_func: mock_line_of_code'
        ),
        id='test__format_traceback_zero_lineno',
    ),
    pytest.param(
        [FrameSummary('mock_file.py', 42, 'mock_func')],
        (
            '⟶ mock_file.py\n'
            '  42, mock_func'
        ),
        id='test__format_traceback_no_source',
    ),
    pytest.param(
        [
            FrameSummary('mock_file.py',  42, 'mock_func_1', line='mock_line_of_code_1'),
            FrameSummary('mock_file.py',  77, 'mock_func_2', line='mock_line_of_code_2'),
            FrameSummary('mock_file.py', 137, 'mock_func_3', line='mock_line_of_code_3'),
        ],
        (
            '⟶ mock_file.py\n'
            '  42, mock_func_1: mock_line_of_code_1\n'
            '  77, mock_func_2: mock_line_of_code_2\n'
            '  137, mock_func_3: mock_line_of_code_3'
        ),
        id='test__format_traceback_single_file',
    ),
    pytest.param(
        [
            FrameSummary('mock_file_1.py',  42, 'mock_func_1_1', line='mock_line_of_code_1_1'),
            FrameSummary('mock_file_1.py',  77, 'mock_func_1_2', line='mock_line_of_code_1_2'),
            FrameSummary('mock_file_1.py', 137, 'mock_func_1_3', line='mock_line_of_code_1_3'),
            FrameSummary('mock_file_2.py',  42, 'mock_func_2_1', line='mock_line_of_code_2_1'),
            FrameSummary('mock_file_2.py',  77, 'mock_func_2_2', line='mock_line_of_code_2_2'),
            FrameSummary('mock_file_2.py', 137, 'mock_func_2_3', line='mock_line_of_code_2_3'),
            FrameSummary('mock_file_3.py',  42, 'mock_func_3_1', line='mock_line_of_code_3_1'),
            FrameSummary('mock_file_3.py',  77, 'mock_func_3_2', line='mock_line_of_code_3_2'),
            FrameSummary('mock_file_3.py', 137, 'mock_func_3_3', line='mock_line_of_code_3_3'),
        ],
        (
            '⟶ mock_file_1.py\n'
            '  42, mock_func_1_1: mock_line_of_code_1_1\n'
            '  77, mock_func_1_2: mock_line_of_code_1_2\n'
            '  137, mock_func_1_3: mock_line_of_code_1_3\n'
            '⟶ mock_file_2.py\n'
            '  42, mock_func_2_1: mock_line_of_code_2_1\n'
            '  77, mock_func_2_2: mock_line_of_code_2_2\n'
            '  137, mock_func_2_3: mock_line_of_code_2_3\n'
            '⟶ mock_file_3.py\n'
            '  42, mock_func_3_1: mock_line_of_code_3_1\n'
            '  77, mock_func_3_2: mock_line_of_code_3_2\n'
            '  137, mock_func_3_3: mock_line_of_code_3_3'
        ),
        id='test__format_traceback_multiple_files',
    ),
    pytest.param(
        [
            FrameSummary('mock_file_1.py',  42, 'mock_func_1_1', line='mock_line_of_code_1_1'),
            FrameSummary('mock_file_2.py',  42, 'mock_func_2_1', line='mock_line_of_code_2_1'),
            FrameSummary('mock_file_1.py',  77, 'mock_func_1_2', line='mock_line_of_code_1_2'),
        ],
        (
            '⟶ mock_file_1.py\n'
            '  42, mock_func_1_1: mock_line_of_code_1_1\n'
            '⟶ mock_file_2.py\n'
            '  42, mock_func_2_1: mock_line_of_code_2_1\n'
            '⟶ mock_file_1.py\n'
            '  77, mock_func_1_2: mock_line_of_code_1_2'
        ),
        id='test__format_traceback_repeated_file',
    ),
])
# pylint: disable-next=unused-variable
def test__format_traceback(monkeypatch: pytest.MonkeyPatch, frames: list[FrameSummary], expected: str) -> None:
    """Test `_format_traceback()`."""
    def mock_extract_tb (_: TracebackType) -> StackSummary:
        return StackSummary.from_list(frames)
    monkeypatch.setattr(traceback, 'extract_tb', mock_extract_tb)
    assert legion._format_traceback(None) == expected


@pytest.mark.parametrize(('lines', 'expected'), [
    pytest.param(
        [],
        'fallback',
        id='test__format_trackeback_linecache_empty',
    ),
    pytest.param(
        [
            'source_code_part1_',
            '_part2_split_',
            '_part3_end',
        ],
        'source_code_part1__part2_split__part3_end',
        id='test__format_trackeback_linecache_baseline',
    ),

])
# pylint: disable-next=unused-variable
def test__format_traceback_linecache(monkeypatch: pytest.MonkeyPatch, lines: list[str], expected: str) -> None:
    """Test `_format_traceback()` `linecache` handling and fallback."""
    def mock_extract_tb (_: TracebackType) -> StackSummary:
        return StackSummary.from_list([FrameSummary('mock_file.py', 1, 'mock_func', end_lineno=3, line='fallback')])
    monkeypatch.setattr(traceback, 'extract_tb', mock_extract_tb)
    def mock_getlines(filename: str, *_: object) -> list[str]:
        assert filename == 'mock_file.py'
        return lines
    monkeypatch.setattr('linecache.getlines', mock_getlines)
    assert legion._format_traceback(None) == f'⟶ mock_file.py\n  1, mock_func: {expected}'


@pytest.mark.parametrize(('code', 'expected_type'), [
    pytest.param(
        'raise ValueError',
        'ValueError',
        id='test_excepthook_exception_resolution_plain_raise',
    ),
    pytest.param(
        'try: raise ValueError\nexcept ValueError as e: raise RuntimeError from e',
        'ValueError',
        id='test_excepthook_exception_resolution_with_cause',
    ),
    pytest.param(
        'try: raise ValueError\nexcept ValueError: raise RuntimeError',
        'ValueError',
        id='test_excepthook_exception_resolution_with_context',
    ),
    pytest.param(
        'try: raise ValueError\nexcept ValueError: raise RuntimeError from None',
        'RuntimeError',
        id='test_excepthook_exception_resolution_suppressed',
    ),
])
# pylint: disable-next=unused-variable
def test_excepthook_exception_resolution(monkeypatch: pytest.MonkeyPatch, code: str, expected_type: str) -> None:
    """Test `excepthook()` exception nesting resolution."""
    def mock_format_message(heading: str, *_: object) -> str:
        return heading
    monkeypatch.setattr(legion, 'format_message', mock_format_message)

    def mock_logger_error(message: str, *_: object) -> str:
        return message
    error_spy = CallableSpy(mock_logger_error)
    monkeypatch.setattr(legion.Logger, 'error', error_spy)

    try:
        exec(code)  # noqa: S102  # pylint: disable=exec-used
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        legion.excepthook(type(exc), exc, exc.__traceback__)

    assert f'({expected_type})' in error_spy.calls[0][0]


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

"""Test units for `excepthook()` function and helpers."""
import errno
from os import strerror
import sys
import traceback
from traceback import FrameSummary, StackSummary
from typing import TYPE_CHECKING

import pytest

# pyright: reportPrivateUsage=false
from legion import (
    _format_exception,
    _get_exception_chain,
    _munge_exception_args,
    _munge_exception_traceback,
    excepthook,
)
from tests.helpers import CallableSpy

if TYPE_CHECKING:
    from types import TracebackType


@pytest.mark.parametrize(('code', 'expected'), [
    pytest.param(
        'raise ValueError',
        [('ValueError', '')],
        id='test_excepthook_get_exception_chain_plain_raise',
    ),
    pytest.param(
        'try: raise ValueError\nexcept ValueError as e: raise RuntimeError from e',
        [
            ('ValueError', ''),
            ('RuntimeError', ' __cause__ '),
        ],
        id='test_excepthook_get_exception_chain_with_cause',
    ),
    pytest.param(
        'try: raise ValueError\nexcept ValueError: raise RuntimeError',
        [
            ('ValueError', ''),
            ('RuntimeError', '__context__'),
        ],
        id='test_excepthook_get_exception_chain_with_context',
    ),
    pytest.param(
        'try: raise ValueError\nexcept ValueError: raise RuntimeError from None',
        [
            ('RuntimeError', ''),
        ],
        id='test_excepthook_get_exception_chain_suppressed',
    ),
])
# pylint: disable-next=unused-variable
def test_excepthook__get_exception_chain(code: str, expected: list[tuple[str, str]]) -> None:
    """Test `_get_exception_chain()`."""
    try:
        exec(code)  # noqa: S102  # pylint: disable=exec-used
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        chain = _get_exception_chain(exc)
        chain = [(type(exc).__name__, marker) for (exc, marker) in chain]
        assert chain == expected


# pylint: disable-next=unused-variable
def test_excepthook_keyboard_interrupt_handling() -> None:
    """Test `KeyboardInterrupt` handling."""
    sys.__excepthook__ = CallableSpy(sys.__excepthook__)
    sys.excepthook = excepthook

    exc = KeyboardInterrupt()
    args = (KeyboardInterrupt, exc, exc.__traceback__)
    excepthook(KeyboardInterrupt, exc, exc.__traceback__)

    assert sys.__excepthook__.called
    assert sys.__excepthook__.calls[0][1] == args


@pytest.mark.parametrize(('exception', 'expected'), [
    pytest.param(
        OSError(errno.ENOENT, strerror(errno.ENOENT) + '...', 'mock_filename1.txt', errno.ENOENT, 'mock_filename2.txt'),
        [
            (' errcodes', f'{errno.errorcode[errno.ENOENT]}/WinError{errno.ENOENT}'),
            (' strerror', strerror(errno.ENOENT)),
            ('filename1', 'mock_filename1.txt'),
            ('filename2', 'mock_filename2.txt'),
        ],
        id='test_excepthook__munge_exception_args_oserror_baseline',
    ),
    pytest.param(
        OSError(errno.ENOENT, None, 'mock_filename1.txt', errno.ENOENT),
        [
            (' errcodes', f'{errno.errorcode[errno.ENOENT]}/WinError{errno.ENOENT}'),
            (' strerror', None),
            ('filename1', 'mock_filename1.txt'),
            ('filename2', None),
        ],
        id='test_excepthook__munge_exception_args_oserror_partial',
    ),
    pytest.param(
        OSError(),
        [
            (' errcodes', 'WinErrorNone'),
            (' strerror', None),
            ('filename1', None),
            ('filename2', None),
        ],
        id='test_excepthook__munge_exception_args_oserror_void',
    ),
    pytest.param(
        Exception('mock message', 42, 3.14, True),  # noqa: FBT003
        [
            ('  str', 'mock message'),
            ('  int', 42),
            ('float', 3.14),
            (' bool', True),
        ],
        id='test_excepthook__munge_exception_args_exception',
    ),
    pytest.param(
        Exception(),
        [],
        id='test_excepthook__munge_exception_args_void',
    ),
    pytest.param(
        Exception(None),
        [('NoneType', None)],
        id='test_excepthook__munge_exception_args_none',
    ),
    pytest.param(
        Exception(''),
        [('str', '')],
        id='test_excepthook__munge_exception_args_empty',
    ),
    pytest.param(
        Exception(' ' * 42),
        [('str', ' ' * 42)],
        id='test_excepthook__munge_exception_args_whitespace',
    ),
])
# pylint: disable-next=unused-variable
def test_excepthook__munge_exception_args(exception: Exception, expected: list[tuple[str, str]]) -> None:
    """Test `_munge_exception_args()`."""
    assert _munge_exception_args(exception) == [(label, repr(value)) for (label, value) in expected]


@pytest.mark.parametrize(('frames', 'expected'), [
    pytest.param(
        [],  # This tests `None` tracebacks, too.
        [],
        id='test_excepthook__munge_exception_traceback_no_frames',
    ),
    pytest.param(
        [FrameSummary('mock_file.py', 42, 'mock_func', line='mock_line_of_code')],
        [('mock_file.py', '42', 'mock_func', 'mock_line_of_code')],
        id='test_excepthook__munge_exception_traceback_single_frame',
    ),
    pytest.param(
        [
            FrameSummary('mock_file_1.py',  42, 'mock_func_1', line='mock_line_of_code_1'),
            FrameSummary('mock_file_2.py',  77, 'mock_func_2', line='mock_line_of_code_2'),
            FrameSummary('mock_file_3.py', 137, 'mock_func_3', line='mock_line_of_code_3'),
        ],
        [
            ('mock_file_1.py',  '42', 'mock_func_1', 'mock_line_of_code_1'),
            ('mock_file_2.py',  '77', 'mock_func_2', 'mock_line_of_code_2'),
            ('mock_file_3.py', '137', 'mock_func_3', 'mock_line_of_code_3'),
        ],
        id='test_excepthook__munge_exception_traceback_multiple_frames',
    ),
    pytest.param(
        [FrameSummary('mock_file.py', None, 'mock_func', line='mock_line_of_code')],
        [('mock_file.py', '1', 'mock_func', 'mock_line_of_code')],
        id='test_excepthook__munge_exception_traceback_none_lineno',
    ),
    pytest.param(
        [FrameSummary('mock_file.py', 0, 'mock_func', line='mock_line_of_code')],
        [('mock_file.py', '1', 'mock_func', 'mock_line_of_code')],
        id='test_excepthook__munge_exception_traceback_zero_lineno',
    ),
    pytest.param(
        [FrameSummary('mock_file.py', 42, 'mock_func')],
        [('mock_file.py', '42', 'mock_func', '')],
        id='test_excepthook__munge_exception_traceback_no_source',
    ),
])
# pylint: disable-next=unused-variable
def test_excepthook__munge_exception_traceback(
    monkeypatch: pytest.MonkeyPatch,
    frames: list[FrameSummary],
    expected: str,
) -> None:
    """Test `_munge_exception_traceback()`."""
    def mock_extract_tb (_: TracebackType) -> StackSummary:
        return StackSummary.from_list(frames)
    monkeypatch.setattr(traceback, 'extract_tb', mock_extract_tb)
    assert _munge_exception_traceback(Exception()) == expected


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
def test_excepthook__munge_exception_traceback_linecache(
    monkeypatch: pytest.MonkeyPatch,
    lines: list[str],
    expected: str,
) -> None:
    """Test `_munge_exception_traceback()` `linecache` handling and fallback."""
    def mock_extract_tb (_: TracebackType) -> StackSummary:
        return StackSummary.from_list([FrameSummary('mock_file.py', 1, 'mock_func', end_lineno=3, line='fallback')])
    monkeypatch.setattr(traceback, 'extract_tb', mock_extract_tb)
    def mock_getlines(filename: str, *_: object) -> list[str]:
        assert filename == 'mock_file.py'
        return lines
    monkeypatch.setattr('linecache.getlines', mock_getlines)
    assert _munge_exception_traceback(Exception()) == [('mock_file.py', '1', 'mock_func', expected)]


@pytest.mark.parametrize(('marker', 'expected'), [
    pytest.param('', '', id='test_excepthook__format_exception_chain_marker_empty'),
    pytest.param('mock_marker', '[mock_marker] ', id='test_excepthook__format_exception_chain_marker_baseline'),
])
# pylint: disable-next=unused-variable
def test_excepthook__format_exception_header(marker: str, expected: str) -> None:
    """Test `_format_exception()` header handling."""
    exc = Exception()
    result = _format_exception(exc, marker)
    assert type(exc).__name__ in result
    assert expected in result


@pytest.mark.parametrize(('arguments', 'expected'), [
    pytest.param(
        [],
        '',
        id='test_excepthook__format_exception_arguments_empty',
    ),
    pytest.param(
        [('str', 'string'), ('NoneType', 'None'), ('str', ''), ('float', 3.14)],
        (
            "  str: 'string'\n"
            "  NoneType: 'None'\n"
            "  str: ''\n"
            "  float: 3.14\n"
            '\n'
        ),
        id='test_excepthook__format_exception_arguments_baseline',
    ),
    pytest.param(
        [('very_long_label', 'value1'), ('   padded_label', 'value2')],
        (
            "  very_long_label: 'value1'\n"
            "     padded_label: 'value2'\n"
            '\n'
        ),
        id='test_excepthook__format_exception_arguments_honor_padding',
    ),
])
# pylint: disable-next=unused-variable
def test_excepthook__format_exception_args(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[tuple[str, str]],
    expected: str,
) -> None:
    """Test `_format_exception()` exception arguments handling."""
    def _mock__munge_exception_args(*_: object) -> list[tuple[str, str]]:
        return [(label, repr(value)) for (label, value) in arguments]
    monkeypatch.setattr('legion._munge_exception_args', _mock__munge_exception_args)

    result = _format_exception(Exception(), '')

    assert result.split('\n')[1:] == expected.split('\n')


@pytest.mark.parametrize(('frames', 'expected'), [
    pytest.param(
        [],
        '',
        id='test_excepthook__format_exception_traceback_empty',
    ),
    pytest.param(
        [('mock_file.py', '42', 'mock_func', 'mock_line_of_code')],
        (
            '  > mock_file.py:\n'
            '    42, mock_func: mock_line_of_code\n'
        ),
        id='test_excepthook__format_exception_traceback_baseline',
    ),
    pytest.param(
        [
            ('mock_file_1.py',  '42', 'mock_func_1', 'mock_line_of_code_1'),
            ('mock_file_1.py',  '77', 'mock_func_1', 'mock_line_of_code_2'),
            ('mock_file_1.py', '137', 'mock_func_1', 'mock_line_of_code_3'),
            ('mock_file_2.py',  '42', 'mock_func_2', 'mock_line_of_code_1'),
            ('mock_file_2.py',  '77', 'mock_func_2', 'mock_line_of_code_2'),
            ('mock_file_2.py', '137', 'mock_func_2', 'mock_line_of_code_3'),
            ('mock_file_1.py',  '42', 'mock_func_1', 'mock_line_of_code_1'),
            ('mock_file_1.py',  '77', 'mock_func_1', 'mock_line_of_code_2'),
            ('mock_file_1.py', '137', 'mock_func_1', 'mock_line_of_code_3'),
        ],
        (
            '  > mock_file_1.py:\n'
            '    42, mock_func_1: mock_line_of_code_1\n'
            '    77, mock_func_1: mock_line_of_code_2\n'
            '    137, mock_func_1: mock_line_of_code_3\n'
            '  > mock_file_2.py:\n'
            '    42, mock_func_2: mock_line_of_code_1\n'
            '    77, mock_func_2: mock_line_of_code_2\n'
            '    137, mock_func_2: mock_line_of_code_3\n'
            '  > mock_file_1.py:\n'
            '    42, mock_func_1: mock_line_of_code_1\n'
            '    77, mock_func_1: mock_line_of_code_2\n'
            '    137, mock_func_1: mock_line_of_code_3\n'
        ),
        id='test_excepthook__format_exception_traceback_many_files',
    ),
])
# pylint: disable-next=unused-variable
def test_excepthook__format_exception_traceback(
    monkeypatch: pytest.MonkeyPatch,
    frames: list[tuple[str, str, str, str]],
    expected:str,
) -> None:
    """Test `_format_exception()` exception arguments handling."""
    def _mock__munge_exception_traceback(*_: object) -> list[tuple[str, str, str, str]]:
        return frames
    monkeypatch.setattr('legion._munge_exception_traceback', _mock__munge_exception_traceback)

    result = _format_exception(Exception(), '')

    assert result.split('\n')[1:] == expected.split('\n')


# pylint: disable-next=unused-variable
def test_excepthook(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `excepthook()` functionality."""
    mock_exception_chain = [(Exception(), ''), (Exception(), 'mock_marker')]
    mock_formatted_exception = 'Formatted exception'
    mock_formatted_message = 'Formatted message.'
    _get_exception_chain_spy = CallableSpy(lambda *_: mock_exception_chain)
    _format_exception_spy = CallableSpy(lambda *_: mock_formatted_exception)
    format_message_spy = CallableSpy(lambda *_: mock_formatted_message)
    error_spy = CallableSpy(lambda *_: None)
    monkeypatch.setattr('legion._get_exception_chain', _get_exception_chain_spy)
    monkeypatch.setattr('legion._format_exception', _format_exception_spy)
    monkeypatch.setattr('legion.format_message', format_message_spy)
    monkeypatch.setattr('legion.Logger.error', error_spy)

    exc = Exception()
    excepthook(Exception, exc, None)
    for spy in (_get_exception_chain_spy, format_message_spy, error_spy):
        assert spy.called
        assert len(spy.calls) == 1
    assert _format_exception_spy.called
    assert len(_format_exception_spy.calls) == len(mock_exception_chain)
    assert _get_exception_chain_spy.calls[0] == (mock_exception_chain, (exc,), {})
    assert _format_exception_spy.calls[0] == (mock_formatted_exception, mock_exception_chain[0], {})
    assert _format_exception_spy.calls[1] == (mock_formatted_exception, mock_exception_chain[1], {})
    assert error_spy.calls[0] == (None, (mock_formatted_message,), {})

    default_format_message_args = ('Unhandled exception', (mock_formatted_exception + '\n') * 2)
    custom_format_message_args = ('Customized header', (mock_formatted_exception + '\n') * 2)
    assert format_message_spy.calls[0] == (mock_formatted_message, default_format_message_args, {})

    excepthook(Exception, Exception(), None, heading=custom_format_message_args[0])
    assert format_message_spy.calls[1] == (mock_formatted_message, custom_format_message_args, {})

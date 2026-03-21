#! /usr/bin/env python3
"""Test suite for `excepthook()` function and helpers."""
import errno
import logging
from os import strerror
from random import choice, randint
from string import ascii_lowercase
import sys
import traceback
from traceback import FrameSummary, StackSummary
from typing import TYPE_CHECKING

import pytest

# ruff: disable[SLF001]  # pylint: disable=protected-access
# pyright: reportPrivateUsage=false
import legion
from tests.helpers import CallableSpy, strip_logging_noise

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from tests.helpers import LogPaths


def test_excepthook_keyboard_interrupt_handling() -> None:  # pylint: disable=unused-variable
    """Test `KeyboardInterrupt` handling."""
    sys.__excepthook__ = CallableSpy(sys.__excepthook__)
    sys.excepthook = legion.excepthook

    exc = KeyboardInterrupt()
    args = (KeyboardInterrupt, exc, exc.__traceback__)
    legion.excepthook(KeyboardInterrupt, exc, exc.__traceback__)

    assert sys.__excepthook__.called
    assert sys.__excepthook__.calls[0][1] == args


@pytest.mark.parametrize(('exc_type', 'arg_labels', 'arg_values', 'munger'), [
    pytest.param(
        OSError,
        legion._OSERROR_ATTRIBUTE_LABELS,
        (errno.ENOENT, strerror(errno.ENOENT), 'filename1', errno.ENOENT, 'filename2'),
        lambda e: legion.munge_oserror(e)[1:], # pyright: ignore[reportUnknownArgumentType,reportUnknownLambdaType]
        id='test_excepthook_format_oserror_details',
    ),
    pytest.param(
        Exception,
        ('str', 'int'),
        ('sample', 42),
        lambda e: e.args, # pyright: ignore[reportUnknownArgumentType,reportUnknownLambdaType,reportUnknownMemberType]
        id='test_excepthook_format_exception_details',
    ),
])
# pylint: disable-next=unused-variable
def test_excepthook_format_exception_details(
    exc_type: type[BaseException],
    arg_labels: tuple[str, ...],
    arg_values: tuple[object, ...],
    munger: Callable[[BaseException], tuple[object, ...]],
) -> None:
    """Test `_format_exception_details`."""
    exc = exc_type(*arg_values)
    label_maxlen = max((len(label) for label in arg_labels), default=0)

    munged_args = munger(exc)
    output: list[str] = []
    for label, value in zip(arg_labels, munged_args, strict=True):
        output.append(legion._EXCEPTION_ATTRIBUTE_TEMPLATE.format(label, label_maxlen, value))
    expected = '\n'.join(output)

    assert legion._format_exception_details(exc) == expected


def test_excepthook_format_traceback(monkeypatch: pytest.MonkeyPatch) -> None:  # pylint: disable=unused-variable
    """Test `_format_traceback()`."""
    min_items = 3
    max_items = 9
    min_lineno = 1
    max_lineno = 999

    expected = ''
    mock_frames: list[FrameSummary] = []

    # ruff: disable[S311]
    for _i in range(randint(min_items, max_items)):
        filename = f'source_file_{choice(ascii_lowercase)}.py'
        expected += legion._TRACEBACK_FRAME_HEADING_TEMPLATE.format(filename)
        for _j in range(randint(min_items, max_items)):
            location = (randint(min_lineno, max_lineno), f'func_{choice(ascii_lowercase)}')
            codeline = f'source_code_{choice(ascii_lowercase)}'
            mock_frames.append(FrameSummary(filename, *location, line=codeline))
            expected += legion._TRACEBACK_FRAME_LOCATION_TEMPLATE.format(*location, codeline)
    # ruff: enable[S311]

    def patched_extract_tb (_: TracebackType) -> StackSummary:
        return StackSummary.from_list(mock_frames)

    monkeypatch.setattr(traceback, 'extract_tb', patched_extract_tb)

    assert legion._format_traceback(None) == expected


@pytest.mark.parametrize(('has_args', 'has_traceback'), [
    pytest.param(True, True, id='test_excepthook_formatting_full_output'),
    pytest.param(False, True, id='test_excepthook_formatting_no_details'),
    pytest.param(True, False, id='test_excepthook_formatting_no_traceback'),
    pytest.param(False, False, id='test_excepthook_formatting_no_output'),
])
# pylint: disable-next=unused-variable
def test_excephook_formatting(
    monkeypatch: pytest.MonkeyPatch,
    log_paths: LogPaths,
    capsys: pytest.CaptureFixture[str],
    has_args: bool,  # noqa: FBT001
    has_traceback: bool,  # noqa: FBT001
) -> None:
    """Test `excepthook` full formatting."""
    def patched_extract_tb(_: TracebackType) -> StackSummary:
        return StackSummary.from_list([FrameSummary('filename.py', 1, 'func', line='codeline')])

    monkeypatch.setattr(traceback, 'extract_tb', patched_extract_tb)

    legion.get_logger(__name__).config(main_log_output=log_paths.log, full_log_output=log_paths.trace)

    exc = Exception(*((42,) if has_args else ()))
    legion.excepthook(type(exc), exc, exc.__traceback__ if has_traceback else None)
    logging.shutdown()

    heading = legion._EXCEPTHOOK_HEADING_TEMPLATE.format(legion._DEFAULT_EXCEPTHOOK_HEADING, type(exc).__name__)
    formatted_details = legion._format_exception_details(exc)
    if formatted_traceback := legion._format_traceback(exc.__traceback__):
        formatted_details += '\n\n' if formatted_details else ''
        formatted_details += formatted_traceback

    expected = legion.format_message(heading, formatted_details).split('\n')
    expected.append('')

    main_log_file_contents = log_paths.log.read_text(encoding=legion.UTF8)
    main_log_file_contents = [strip_logging_noise(line) for line in main_log_file_contents.split('\n')]
    assert main_log_file_contents == expected

    full_log_file_contents = log_paths.trace.read_text(encoding=legion.UTF8)
    full_log_file_contents = [strip_logging_noise(line) for line in full_log_file_contents.split('\n')]
    assert full_log_file_contents == expected

    captured_output = capsys.readouterr()

    assert not captured_output.out
    assert captured_output.err == '\n'.join(expected)


# ruff: enable[SLF001]  # pylint: enable=protected-access

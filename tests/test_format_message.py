#! /usr/bin/env python3
"""Test suite for `error()` function."""
from string import whitespace

import pytest

from legion import format_message

MULTIPLIER = 42
MESSAGE = 'message'
DETAILS = 'details'
DETAILS_SEP = '\n'
INDENT = '*' * MULTIPLIER
DEFAULT_INDENT = ' '
@pytest.mark.parametrize(('message', 'details', 'details_indent', 'expected'), [
    pytest.param(
        None, None, None, '',
        id = 'format_message-no_arguments',
    ),
    pytest.param(
        whitespace, whitespace, None, '',
        id = 'format_message-empty_arguments',
    ),
    pytest.param(
        None, DETAILS, None, f'{DEFAULT_INDENT}{DETAILS}',
        id = 'format_message-missing_message',
    ),
    pytest.param(
        MESSAGE, None, None, MESSAGE,
        id = 'format_message-missing_details',
    ),
    pytest.param(
        None, f'{DETAILS}\n\n{DETAILS}', None, f'{DEFAULT_INDENT}{DETAILS}\n\n{DEFAULT_INDENT}{DETAILS}',
        id = 'format_message-multiline_details',
    ),
    pytest.param(
        None, DETAILS, INDENT, f'{INDENT}{DETAILS}',
        id = 'format_message-custom_details_indent',
    ),
    pytest.param(
        MESSAGE, f'{DETAILS}\n{DETAILS}', INDENT, f'{MESSAGE}{DETAILS_SEP}{INDENT}{DETAILS}\n{INDENT}{DETAILS}',
        id = 'format_message-full_featured',
    ),
])
# pylint: disable-next=unused-variable
def test_output(message: str | None, details: str | None, details_indent: str | None, expected: str) -> None:
    """Test output depending on the arguments."""
    kwargs = {k: v for k, v in {
        'message': message,
        'details': details,
        'details_indent': details_indent,
    }.items() if v is not None}
    output = format_message(**kwargs)
    assert output == expected


def test_format_message_sanitize_message() -> None:  # pylint: disable=unused-variable
    """Test message sanitization."""
    message = whitespace + f'{MESSAGE}{whitespace}{MESSAGE}' * MULTIPLIER + whitespace
    expected = whitespace + f'{MESSAGE} {MESSAGE}' * MULTIPLIER
    output = format_message(message)
    assert output == expected

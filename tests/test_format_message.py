#! /usr/bin/env python3
"""Test suite for `error()` function."""
from string import whitespace

import pytest

from legion import format_message

MESSAGE = 'message'
DETAILS = 'details'
DETAILS_SEP = '\n'
INDENT = '*' * 42
DEFAULT_INDENT = ' '
@pytest.mark.parametrize(('message', 'details', 'details_indent', 'expected'), [
    (None, None, None, ''),
    ('  ', '  ', None, ''),
    (None, DETAILS, None, f'{DETAILS_SEP}{DEFAULT_INDENT}{DETAILS}'),
    (MESSAGE, None, None, MESSAGE),
    (None, f'{DETAILS}\n{DETAILS}', None, f'{DETAILS_SEP}{DEFAULT_INDENT}{DETAILS}\n{DEFAULT_INDENT}{DETAILS}'),
    (None, DETAILS, INDENT, f'{DETAILS_SEP}{INDENT}{DETAILS}'),
    (MESSAGE, f'{DETAILS}\n{DETAILS}', INDENT, f'{MESSAGE}{DETAILS_SEP}{INDENT}{DETAILS}\n{INDENT}{DETAILS}'),
], ids=[
    'no_arguments',
    'empty_arguments',
    'missing_message',
    'missing_details',
    'multiline_details',
    'custom_details_indent',
    'full_featured',
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


def test_sanitize_message() -> None:  # pylint: disable=unused-variable
    """Test message sanitization."""
    message = whitespace + f'{MESSAGE}{whitespace}{MESSAGE}' * 42 + whitespace
    expected = whitespace + f'{MESSAGE} {MESSAGE}' * 42
    output = format_message(message)
    assert output == expected

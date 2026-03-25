#! /usr/bin/env python3
"""Test suite for `error()` function."""
from string import whitespace

import pytest

from legion import format_message

MULTIPLIER = 42
HEADING = 'heading'
MESSAGE = 'message'
SEPARATOR = '\n'
INDENTATION = '*' * MULTIPLIER
DEFAULT_INDENTATION = ' '
@pytest.mark.parametrize(('heading', 'message', 'indentation', 'expected'), [
    pytest.param(
        None, None, None,
        '',
        id = 'test_format_message_None_arguments',
    ),
    pytest.param(
        '', '', None,
        '',
        id = 'test_format_message_empty_arguments',
    ),
    pytest.param(
        '', MESSAGE, None,
        f'{DEFAULT_INDENTATION}{MESSAGE}',
        id = 'test_format_message_missing_heading',
    ),
    pytest.param(
        HEADING, '', None,
        HEADING,
        id = 'test_format_message_missing_message',
    ),
    pytest.param(
        '', f'{MESSAGE}\n\n{MESSAGE}', None,
        f'{DEFAULT_INDENTATION}{MESSAGE}\n\n{DEFAULT_INDENTATION}{MESSAGE}',
        id = 'test_format_message_multiline_message',
    ),
    pytest.param(
        '', MESSAGE, INDENTATION,
        f'{INDENTATION}{MESSAGE}',
        id = 'test_format_message_custom_indentation',
    ),
    pytest.param(
        HEADING, f'{MESSAGE}\n\n{MESSAGE}', INDENTATION,
        f'{HEADING}{SEPARATOR}{INDENTATION}{MESSAGE}\n\n{INDENTATION}{MESSAGE}',
        id = 'test_format_message_full_featured',
    ),
])
# pylint: disable-next=unused-variable
def test_output(heading: str, message: str, indentation: str | None, expected: str) -> None:
    """Test output depending on the arguments."""
    kwargs = {} if indentation is None else {'indentation': indentation}

    output = format_message(heading, message, **kwargs)
    assert output == expected

    if heading == '':
        output = format_message(whitespace, message, **kwargs)
        assert output == expected

    if message == '':
        output = format_message(heading, whitespace, **kwargs)
        assert output == expected


def test_format_message_sanitize_heading() -> None:  # pylint: disable=unused-variable
    """Test heading sanitization."""
    heading = whitespace + f'{HEADING}{whitespace}{HEADING}' * MULTIPLIER + whitespace
    expected = whitespace + f'{HEADING} {HEADING}' * MULTIPLIER
    output = format_message(heading, '')
    assert output == expected

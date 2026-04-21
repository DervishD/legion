"""Test units for the logging system."""
import logging
from typing import NamedTuple, TYPE_CHECKING

import pytest

from legion import get_logger, Logger

from .helpers import LoggingFields, parse_logfile

if TYPE_CHECKING:
    from pathlib import Path

    from .helpers import LoggingPaths


# pylint: disable-next=unused-variable
def test_logging_paths_creation(logging_paths: LoggingPaths) -> None:
    """Test that the logging paths are created propertly."""
    assert not logging_paths.main.is_file()
    assert not logging_paths.full.is_file()

    logger = get_logger(__name__)
    logger.config(main_log_output=logging_paths.main, full_log_output=logging_paths.full)

    assert logging_paths.main.is_file()
    assert logging_paths.full.is_file()

    logging.shutdown()


# pylint: disable-next=unused-variable
def test_logging_console_only_handlers() -> None:
    """Test that proper handlers exist in console-only mode."""
    get_logger(__name__).config()
    handlers = logging.getLogger('').handlers

    for handler in handlers:
        assert type(handler).__name__ == '_LateBindingStreamHandler'
        assert handler.stream_name in ('stdout', 'stderr')  # pyright: ignore  # noqa: PGH003

    logging.shutdown()


# pylint: disable-next=unused-variable
def test_logging_no_handlers() -> None:
    """Test that only `NullHandler` exist in muted mode."""
    get_logger(__name__).config(console=False)

    handlers = logging.getLogger('').handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.NullHandler)

    logging.shutdown()


class OutputSpec(NamedTuple):
    """Expected output abstraction."""  # noqa: D204
    produces_main_log: bool
    produces_full_log: bool
    produces_stdout: bool
    produces_stderr: bool
@pytest.mark.parametrize(('logging_function_name', 'output_spec'), [
   pytest.param('debug', OutputSpec(
        produces_main_log=False,
        produces_full_log=True,
        produces_stdout=False,
        produces_stderr=False,
    ), id='test_logging_functions_debug'),
    pytest.param('info', OutputSpec(
        produces_main_log=True,
        produces_full_log=True,
        produces_stdout=True,
        produces_stderr=False,
    ), id='test_logging_functions_info'),
    pytest.param('warning', OutputSpec(
        produces_main_log=True,
        produces_full_log=True,
        produces_stdout=False,
        produces_stderr=True,
    ), id='test_logging_functions_warning'),
    pytest.param('error', OutputSpec(
        produces_main_log=True,
        produces_full_log=True,
        produces_stdout=False,
        produces_stderr=True,
    ), id='test_logging_functions_error'),
])
# pylint: disable-next=unused-variable,too-many-arguments,too-many-positional-arguments
def test_logging_functions(  # noqa: PLR0913
    request: pytest.FixtureRequest,
    capsys: pytest.CaptureFixture[str],
    logger: Logger,
    logging_paths: LoggingPaths,
    logging_function_name: str,
    output_spec: OutputSpec,
) -> None:
    """Test all logging functions."""
    levelname = logging_function_name.upper()
    funcname = request.function.__name__

    message = 'Test message\nin multiple\n\nlines!\n\n'
    expected = message.split('\n')

    getattr(logger, logging_function_name)(message)

    parsed_main_logfile = parse_logfile(logging_paths.main)
    parsed_full_logfile = parse_logfile(logging_paths.full)

    assert '' not in parsed_main_logfile[LoggingFields.TIMESTAMPS]
    assert '' not in parsed_full_logfile[LoggingFields.TIMESTAMPS]

    assert set(parsed_main_logfile[LoggingFields.FUNCNAMES]) == ({''} if output_spec.produces_main_log else set())
    assert set(parsed_full_logfile[LoggingFields.FUNCNAMES]) == {funcname}

    assert parsed_main_logfile[LoggingFields.MESSAGES] == (expected if output_spec.produces_main_log else [])
    assert parsed_full_logfile[LoggingFields.MESSAGES] == (expected if output_spec.produces_full_log else [])

    assert set(parsed_main_logfile[LoggingFields.LOGLEVELS]) == ({''} if output_spec.produces_main_log else set())
    assert set(parsed_full_logfile[LoggingFields.LOGLEVELS]) == {levelname}

    captured = capsys.readouterr()

    assert captured.out.splitlines() == (expected if output_spec.produces_stdout else [])
    assert captured.err.splitlines() == (expected if output_spec.produces_stderr else [])


@pytest.mark.parametrize('message', [
    pytest.param('No whitespace.', id='test_logging_honor_no_whitespace'),
    pytest.param('   Leading whitespace.', id='test_logging_honor_leading_whitespace'),
    pytest.param('\nLeading newline.', id='test_logging_honor_leading_newline'),
    pytest.param('Trailing newline.\n', id='test_logging_honor_trailing_newline'),
    pytest.param('\bLeading and trailing newline.\n', id='test_logging_honor_both_newlines'),
])
# pylint: disable-next=unused-variable
def test_logging_whitespace_honoring(capsys: pytest.CaptureFixture[str], logger: Logger, message: str) -> None:
    """Test whether whitespace is honored where it should."""
    terminator = '<TERMINATOR>'

    logging.StreamHandler.terminator, saved_terminator = terminator, logging.StreamHandler.terminator
    logger.info(message)
    logging.StreamHandler.terminator = saved_terminator

    captured = capsys.readouterr().out

    assert captured == message + terminator


# pylint: disable-next=unused-variable
def test_logging_indentation(logger: Logger) -> None:
    """Test that logging requested indentation is honored."""
    assert logger.indentation == ''  # pylint: disable=use-implicit-booleaness-not-comparison-to-string

    count = 42

    logger.indent()
    assert logger.indentation == ' '
    for _ in range(count):
        logger.indent()
    assert logger.indentation == ' ' + ' ' * count

    logger.dedent()
    assert logger.indentation == ' ' * count
    for _ in range(count):
        logger.dedent()
    assert logger.indentation == ''  # pylint: disable=use-implicit-booleaness-not-comparison-to-string

    logger.set_indent(count)
    assert logger.indentation == ' ' * count

    logger.set_indent(0)
    assert logger.indentation == ''  # pylint: disable=use-implicit-booleaness-not-comparison-to-string

    invalid_indentation_level = -42
    with pytest.raises(ValueError, match=str(invalid_indentation_level)):
        logger.set_indent(invalid_indentation_level)


# pylint: disable-next=unused-variable
def test_logging_parse_logfile(tmp_path: Path) -> None:
    """Test `parse_logfile()` helper."""
    mock_log_file = tmp_path / 'mock_log_file.log'
    mock_log_file.write_text('invalid_log_line', encoding='utf-8')
    with pytest.raises(ValueError, match='invalid_log_line'):
        parse_logfile(mock_log_file)

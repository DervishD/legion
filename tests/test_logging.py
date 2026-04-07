"""Test units for the logging system."""
import logging
from typing import NamedTuple, TYPE_CHECKING

from tests.helpers import LoggingFields, parse_logfile

if TYPE_CHECKING:
    from tests.helpers import LogPaths

import pytest  # pylint: disable=wrong-import-position,wrong-import-order

import legion  # pylint: disable=wrong-import-position


# pylint: disable-next=unused-variable
def test_logging_paths_creation(log_paths: LogPaths) -> None:
    """Test that the logging paths are created propertly."""
    assert not log_paths.main.is_file()
    assert not log_paths.full.is_file()

    logger = legion.get_logger(__name__)

    logger.config(main_log_output=log_paths.main, full_log_output=log_paths.full)

    logging.shutdown()

    assert log_paths.main.is_file()
    assert log_paths.full.is_file()


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
    logger: legion.Logger,
    log_paths: LogPaths,
    logging_function_name: str,
    output_spec: OutputSpec,
) -> None:
    """Test all logging functions."""
    levelname = logging_function_name.upper()
    funcname = request.function.__name__

    message = 'Test message\nin multiple\n\nlines!\n\n'
    expected = message.split('\n')

    getattr(logger, logging_function_name)(message)

    parsed_main_logfile = parse_logfile(log_paths.main)
    parsed_full_logfile = parse_logfile(log_paths.full)

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
def test_logging_whitespace_honoring(capsys: pytest.CaptureFixture[str], logger: legion.Logger, message: str) -> None:
    """Test whether whitespace is honored where it should."""
    terminator = '<TERMINATOR>'

    logging.StreamHandler.terminator, saved_terminator = terminator, logging.StreamHandler.terminator
    logger.info(message)
    logging.StreamHandler.terminator = saved_terminator

    logging.shutdown()

    captured = capsys.readouterr().out

    assert captured == message + terminator

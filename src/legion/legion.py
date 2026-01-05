#! /usr/bin/env python3
"""Legion.

“What is your name?”
“My name is Legion,” he replied, “for we are many.”

Since the module is many, it's legion.
"""
import atexit
import contextlib
from enum import StrEnum
from errno import errorcode
from importlib.metadata import version
import logging
from logging.config import dictConfig
from os import environ, system
from pathlib import Path
import subprocess
import sys
from textwrap import dedent
from time import strftime
import tomllib
import traceback as tb
from typing import Any, cast, LiteralString, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from io import TextIOWrapper
    from types import TracebackType


__version__ = version(__package__ or Path(__file__).stem)
__all__: list[str] = [  # pylint: disable=unused-variable  # noqa: RUF022
    'DESKTOP_PATH',
    'PROGRAM_PATH',
    'PROGRAM_NAME',
    'LEGION_VERSION',
    'DEFAULT_CREDENTIALS_FILE',
    'TIMESTAMP_FORMAT',
    'ERROR_MARKER',
    'ARROW_R',
    'ARROW_L',
    'UTF8',
    'error',
    'excepthook',
    'munge_oserror',
    'format_oserror',
    'timestamp',
    'run',
    'WFKStatuses',
    'wait_for_keypress',
    'logger',
    'get_credentials',
    'demo',
]


if sys.platform == 'win32':
    from ctypes import byref, c_uint, create_unicode_buffer, windll
    from ctypes.wintypes import MAX_PATH as _MAX_PATH_LEN
    from enum import auto, IntEnum  # pylint: disable=ungrouped-imports
    from msvcrt import get_osfhandle, getch


def _get_desktop_path() -> Path:
    """Get the path of the desktop directory depending on the platform."""
    home_path = Path.home()
    desktop_basename = 'Desktop'

    if sys.platform == 'win32':
        hwnd = 0
        desktop_csidl = 0
        access_token = 0
        shgfp_type_current = 0
        flags = shgfp_type_current
        buffer = create_unicode_buffer(_MAX_PATH_LEN)
        windll.shell32.SHGetFolderPathW(hwnd, desktop_csidl, access_token, flags, buffer)
        return Path(buffer.value)

    if sys.platform == 'darwin':
        return home_path / desktop_basename

    if sys.platform.startswith('linux'):
        try:
            return Path(environ['XDG_DESKTOP_DIR'])
        except KeyError:
            return home_path / desktop_basename

    return home_path


_FALLBACK_PROGRAM_PATH = '__unavailable__.py'
def _get_program_path() -> Path:
    """Get the full, resolved path of the currently executing program."""
    try:
        # This method is not failproof, because there are probably situations
        # where the '__file__' attribute of module '__main__' won't exist but
        # there's some filename involved.
        #
        # If one of those situations arise, the code will be modified accordingly.
        program_path = sys.executable if getattr(sys, 'frozen', False) else sys.modules['__main__'].__file__
    except AttributeError:
        program_path = None
    return Path(program_path or _FALLBACK_PROGRAM_PATH).resolve()


# Exportable constants.
# pylint: disable=unused-variable
DESKTOP_PATH = _get_desktop_path()
PROGRAM_PATH = _get_program_path()

PROGRAM_NAME = PROGRAM_PATH.stem

LEGION_VERSION = __version__

DEFAULT_CREDENTIALS_FILE = Path.home() / '.credentials'

TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'

ERROR_MARKER = '*** '
ARROW_R = '⟶'
ARROW_L = '⟵'

UTF8 = 'utf-8'
# pylint: enable=unused-variable


class _Messages(StrEnum):
    """Module messages."""

    ERROR_HEADER = f'\n{ERROR_MARKER}Error in {PROGRAM_NAME}.'
    ERROR_DETAILS_HEADING = '\nAdditional error information:'
    ERROR_DETAILS_PREAMBLE = '│ '
    ERROR_DETAILS_TAIL = '╰'

    UNEXPECTED_OSERROR = 'Unexpected OSError.'
    OSERROR_DETAILS = dedent("""
         type = {}
        errno = {}
     winerror = {}
     strerror = {}
     filename = {}
    filename2 = {}
    """).strip('\n')
    OSERROR_DETAIL_NA = 'N/A'

    UNHANDLED_EXCEPTION = 'Unhandled exception.'
    EXCEPTION_DETAILS = 'type = {}\nvalue = {}\nargs: {}'
    EXCEPTION_DETAILS_ARG = '\n  [{}] {}'
    TRACEBACK_HEADER = '\n\ntraceback:\n{}'
    TRACEBACK_FRAME_HEADER = '▸ {}\n'
    TRACEBACK_FRAME_LINE = '  {}, {}: {}\n'
    TRACEBACK_TOPLEVEL_FRAME = '<module>'
    ERRDIALOG_TITLE = f'Unexpected error in {PROGRAM_NAME}'

    OSERROR_WINERROR = 'WinError{}'
    OSERROR_ERRORCODES = '{}/{}'
    OSERROR_PRETTYPRINT = 'Error [{}] {} {}.\n{}'

    BAD_INDENTLEVEL = 'Indentation level must be a non-negative integer.'

    PRESS_ANY_KEY = '\nPress any key to continue...'

    DEMO_TIMESTAMP = 'Timestamp is {}\n\n'
    DEMO_CONSTANT = '{:┄<{}}⟶ ⟦{}⟧\n'


_ERROR_PAYLOAD_INDENT = len(ERROR_MARKER)
def error(message: str, details: str = '') -> None:
    """Preprocess and log error message, optionally including details.

    A header/marker is prepended to the message, and a visual separator is
    prepended to the details. Both the message and the details are indented.

    Finally, everything is logged using logging.error().
    """
    message = str(message)
    details = str(details)

    logger.set_indent(0)
    logger.error(_Messages.ERROR_HEADER)

    logger.set_indent(_ERROR_PAYLOAD_INDENT)
    logger.error(message)

    if details := details.strip():
        logger.error(_Messages.ERROR_DETAILS_HEADING)
        logger.error('\n'.join(f'{_Messages.ERROR_DETAILS_PREAMBLE}{line}' for line in details.split('\n')))
        logger.error(_Messages.ERROR_DETAILS_TAIL)

    logger.set_indent(0)


# pylint: disable-next=unused-variable
def excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType | None) -> None:
    """Handle otherwise unhandled exceptions.

    Log information about unhandled exceptions using the provided exception
    information, that is, the exception type, its value and the associated
    traceback.

    For KeyboardInterrupt exceptions, no logging is performed, the default
    exception hook is used instead.

    For OSError exceptions, a different message is logged, including particular
    OSError information, and no traceback is logged.

    For any other unhandled exception, a generic message is logged together with
    the traceback, if available.

    Finally, depending on the platform, some kind of modal dialog is shown so
    the end user does not miss the error.

    Intended to be used as default exception hook (sys.excepthook).
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    if isinstance(exc_value, OSError):
        message = _Messages.UNEXPECTED_OSERROR
        errno_message = _Messages.OSERROR_DETAIL_NA
        if exc_value.errno:
            with contextlib.suppress(IndexError):
                errno_message = errorcode[exc_value.errno]
        details = _Messages.OSERROR_DETAILS.format(
            exc_type.__name__,
            errno_message,
            exc_value.winerror or _Messages.OSERROR_DETAIL_NA,
            exc_value.strerror,
            _Messages.OSERROR_DETAIL_NA if exc_value.filename is None else exc_value.filename,
            _Messages.OSERROR_DETAIL_NA if exc_value.filename2 is None else exc_value.filename2,
        )
    else:
        message = _Messages.UNHANDLED_EXCEPTION
        args = ''
        for arg in exc_value.args:
            args += _Messages.EXCEPTION_DETAILS_ARG.format(type(arg).__name__, arg)
        details = _Messages.EXCEPTION_DETAILS.format(exc_type.__name__, str(exc_value), args)
    current_filename = None
    traceback = ''
    for frame in tb.extract_tb(exc_traceback):
        if current_filename != frame.filename:
            traceback += _Messages.TRACEBACK_FRAME_HEADER.format(frame.filename)
            current_filename = frame.filename
        frame.name = PROGRAM_NAME if frame.name == _Messages.TRACEBACK_TOPLEVEL_FRAME else frame.name
        traceback += _Messages.TRACEBACK_FRAME_LINE.format(frame.lineno, frame.name, frame.line)
    details += _Messages.TRACEBACK_HEADER.format(traceback) if traceback else ''
    error(message, details)

    # Just in case there is NOT a working console or logging system,
    # the error message is also shown in a popup window so the end
    # user is aware of the problem even with uninformative details.
    if sys.platform == 'win32':
        MB_ICONWARNING = 0x30  # pylint: disable=invalid-name  # noqa: N806
        MB_OK = 0  # pylint: disable=invalid-name  # noqa: N806
        windll.user32.MessageBoxW(None, message, _Messages.ERRDIALOG_TITLE, MB_ICONWARNING | MB_OK)
    if sys.platform == 'darwin':
        script = f'display dialog "{message}" with title "{_Messages.ERRDIALOG_TITLE}" with icon caution buttons "OK"'
        system(f"osascript -e '{script}' >/dev/null")  # noqa: S605


def munge_oserror(exception: OSError) -> tuple[str, str, str, str, str]:  # pylint: disable=unused-variable
    """Process OSError exception objects.

    Process the exception object for OSError exceptions (and its subclasses),
    and return a tuple containing the processed information.

    First item is the actual OSError subclass which was raised, as a string.

    Second item is the errno and winerror codes, separated by a slash if both
    are present. If no error codes exist in the exception object, this item is
    replaced by an informative placeholder.

    The third item is the error message, starting with an uppercase letter and
    ending in a period. If it does not exist, it will be an empty string.

    Final two items are the filenames involved in the exception. Depending on
    the actual exception, there may be zero, one or two filenames involved. If
    some of the filenames is not present in the exception object, it will still
    be in the tuple but it's value will be None.
    """
    exc_type = type(exception).__name__
    exc_errno = None
    exc_winerror = None
    exc_errorcodes = None

    with contextlib.suppress(AttributeError):
        exc_winerror = _Messages.OSERROR_WINERROR.format(exception.winerror) if exception.winerror else None

    if exception.errno:
        with contextlib.suppress(KeyError):
            exc_errno = errorcode[exception.errno]

    if exc_errno and exc_winerror:
        exc_errorcodes = _Messages.OSERROR_ERRORCODES.format(exc_errno, exc_winerror)
    exc_errorcodes = exc_errorcodes or exc_errno or exc_winerror or _Messages.OSERROR_DETAIL_NA
    exc_message = ''
    if exception.strerror:
        exc_message = f'{exception.strerror[0].upper()}{exception.strerror[1:].rstrip(".")}.'

    return exc_type, exc_errorcodes, exc_message, exception.filename, exception.filename2


def format_oserror(context: str, exc: OSError) -> str:  # pylint: disable=unused-variable
    """Generate a string from OSError information and the provided context."""
    errorcodes, message, filename, filename2 = munge_oserror(exc)[1:]

    filenames = f"'{filename}'{f" {ARROW_R} '{filename2}'" if filename2 else ''}"
    return _Messages.OSERROR_PRETTYPRINT.format(errorcodes, context, filenames, message)


def timestamp() -> str:  # pylint: disable=unused-variable
    """Produce a timestamp string from current local date and time."""
    return strftime(TIMESTAMP_FORMAT)


# pylint: disable-next=unused-variable
def run(command: Sequence[str], **args: Any) -> subprocess.CompletedProcess[str]:  # noqa: ANN401
    """Run a command.

    Run command (a tuple), using subprocess_args as arguments. This is just a
    helper for subprocess.run() to make such calls more convenient by providing
    a set of defaults for the arguments.

    For that reason, the keyword arguments accepted in subprocess_args and the
    return value for this function are the exact same ones accepted and returned
    by the subprocess.run() function itself.
    """
    default_args: dict[str, Any] = {
        'capture_output': True,
        'check': False,
        'creationflags': 0,
        'errors': 'replace',
        'text': True,
    }
    if sys.platform == 'win32':
        default_args['creationflags'] |= subprocess.CREATE_NO_WINDOW

    effective_args = default_args | args

    # pylint: disable=subprocess-run-check
    return cast('subprocess.CompletedProcess[str]', subprocess.run(command, **effective_args))  # noqa: S603, PLW1510


class _CustomLogger(logging.Logger):
    """Custom logger with indentation support."""

    INCREASE_INDENT_SYMBOL = '+'
    DECREASE_INDENT_SYMBOL = '-'
    INDENTCHAR = ' '
    FORMAT_STYLE = '{'
    DEBUGFILE_FORMAT = '{{asctime}}.{{msecs:04.0f}} {{levelname:{levelname_max_width}}} | {{funcName}}() {{message}}'
    LOGFILE_FORMAT = '{asctime} {message}'
    CONSOLE_FORMAT = '{message}'

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        self.indentlevel: int = 0
        self.indentation = ''

    def makeRecord(self, *args: Any, **kwargs: Any) -> logging.LogRecord:  # noqa: ANN401, N802
        """Create a new logging record with indentation support."""
        record = super().makeRecord(*args, **kwargs)
        record.msg = '\n'.join(f'{self.indentation}{line}'.rstrip() for line in record.msg.split('\n'))
        return record

    def _set_indentlevel(self, level: int | LiteralString) -> None:
        """Set current logging indentation level.

        If level is:
            - INCREASE_INDENT_SYMBOL string, indentation is increased.
            - DECREASE_INDENT_SYMBOL string, indentation is decreased.
            - any non-negative integer, indentation is set to that value.

        For any other value, ValueError is raised.

        Not for public usage, use self.set_indent(level) instead.
        """
        if level == self.INCREASE_INDENT_SYMBOL:
            self.indentlevel += 1
        elif level == self.DECREASE_INDENT_SYMBOL:
            self.indentlevel = max(0, self.indentlevel - 1)
        elif isinstance(level, int) and level >= 0:
            self.indentlevel = level
        else:
            raise ValueError(_Messages.BAD_INDENTLEVEL)
        self.indentation = self.INDENTCHAR * self.indentlevel

    def set_indent(self, level: int) -> None:
        """Set current logging indentation level."""
        self._set_indentlevel(level)

    def indent(self) -> None:
        """Increment current logging indentation level."""
        self._set_indentlevel(self.INCREASE_INDENT_SYMBOL)

    def dedent(self) -> None:
        """Decrement current logging indentation level."""
        self._set_indentlevel(self.DECREASE_INDENT_SYMBOL)

    def config(self,
        debugfile: str|Path|None = None,
        logfile: str|Path|None = None,
        console: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """Configure logger.

        With the default configuration ALL logging messages are sent to
        debugfile with a timestamp and some debugging information; those
        messages with severity of logging.INFO or higher are sent to logfile,
        also timestamped.

        In addition to that, and if console is True (the default), messages with
        a severity of logging.INFO (and only those) are sent to the standard
        output stream, and messages with a severity of logging.WARNING or higher
        are sent to the standard error stream, without a timestamp in both
        cases.

        If debugfile or logfile are None (the default), then the corresponding
        files are not created and no logging message will go there. In this
        case, if console is False, NO LOGGING OUTPUT WILL BE PRODUCED AT ALL.
        """
        class _CustomFormatter(logging.Formatter):
            """Simple custom formatter with multiline support."""  # noqa: D204
            def format(self, record: logging.LogRecord) -> str:
                """Format multiline records so they look like multiple records."""
                formatted_record = super().format(record)
                preamble = formatted_record[0:formatted_record.rfind(record.message)]
                return '\n'.join(f'{preamble}{line}'.rstrip() for line in record.message.split('\n'))

        logging_configuration: dict[str, Any] = {
            'version': 1,
            'disable_existing_loggers': False,
            'loggers': {
                self.name: {
                    'level': logging.NOTSET,
                    'propagate': False,
                    'handlers': [],
                },
            },
        }

        formatters = {}
        handlers = {}

        if debugfile:
            levelname_max_len = len(max(logging.getLevelNamesMapping(), key=len))
            formatters['debugfile_formatter'] = {
                '()': _CustomFormatter,
                'style': self.FORMAT_STYLE,
                'format': self.DEBUGFILE_FORMAT.format(levelname_max_width=levelname_max_len),
                'datefmt': TIMESTAMP_FORMAT,
            }
            handlers['debugfile_handler'] = {
                'level': logging.NOTSET,
                'formatter': 'debugfile_formatter',
                'class': logging.FileHandler,
                'filename': debugfile,
                'mode': 'w',
                'encoding': UTF8,
            }

        if logfile:
            formatters['logfile_formatter'] = {
                '()': _CustomFormatter,
                'style': self.FORMAT_STYLE,
                'format': self.LOGFILE_FORMAT,
                'datefmt': TIMESTAMP_FORMAT,
            }
            handlers['logfile_handler'] = {
                'level': logging.INFO,
                'formatter': 'logfile_formatter',
                'class': logging.FileHandler,
                'filename': logfile,
                'mode': 'w',
                'encoding': UTF8,
            }

        if console:
            def console_filter(record: logging.LogRecord) -> bool:
                """Filter records for StreamHandler objects."""
                return record.levelno == logging.INFO

            formatters['console_formatter'] = {
                '()': _CustomFormatter,
                'style': self.FORMAT_STYLE,
                'format': self.CONSOLE_FORMAT,
            }
            handlers['stdout_handler'] = {
                'level': logging.NOTSET,
                'formatter': 'console_formatter',
                'filters': [console_filter],
                'class': logging.StreamHandler,
                'stream': sys.stdout,
            }
            handlers['stderr_handler'] = {
                'level': logging.WARNING,
                'formatter': 'console_formatter',
                'class': logging.StreamHandler,
                'stream': sys.stderr,
            }

        logging_configuration['formatters'] = formatters
        logging_configuration['handlers'] = handlers
        logging_configuration['loggers'][self.name]['handlers'] = handlers.keys()
        dictConfig(logging_configuration)


if sys.platform == 'win32':
    class WFKStatuses(IntEnum):
        """Return statuses for wait_for_keypress()."""  # noqa: D204
        NO_WIN32 = auto()
        NO_CONSOLE_ATTACHED = auto()
        NO_CONSOLE_TITLE = auto()
        NO_TRANSIENT_FROZEN = auto()
        NO_TRANSIENT_PYTHON = auto()
        WAIT_FOR_KEYPRESS = auto()

    @atexit.register
    def wait_for_keypress() -> WFKStatuses:  # pylint: disable=unused-variable,too-many-return-statements
        """Wait for a keypress to continue if sys.stdout is a real console AND the console is transient."""
        if sys.platform != 'win32':
            return WFKStatuses.NO_WIN32

        PYTHON_LAUNCHER = Path('py.exe')  # pylint: disable=invalid-name  # noqa: N806

        # If no console is attached, then the application must NOT pause.
        #
        # Since sys.stdout.isatty() returns True under Windows when sys.stdout
        # is redirected to NUL, another (more complex) method, is needed here.
        # The test below has been adapted from https://stackoverflow.com/a/33168697
        if not windll.kernel32.GetConsoleMode(get_osfhandle(sys.stdout.fileno()), byref(c_uint())):
            return WFKStatuses.NO_CONSOLE_ATTACHED

        # If there is a console attached, the application must pause ONLY if that
        # console will automatically close when the application finishes, hiding
        # any messages printed by the application. In other words, pause only if
        # the console is transient.
        #
        # Determining if a console is transient is not easy as there is no
        # bulletproof method available for every possible circumstance.
        #
        # There are TWO main scenarios: a frozen executable and a .py file.
        # In both cases, the console title has to be obtained.
        buffer_size = _MAX_PATH_LEN + 1
        console_title = create_unicode_buffer(buffer_size)
        if not windll.kernel32.GetConsoleTitleW(console_title, buffer_size):
            return WFKStatuses.NO_CONSOLE_TITLE
        console_title = console_title.value

        # If the console is not transient, return, do not pause.
        #
        # For a frozen executable, it is more or less easy: if the console title
        # is not equal to sys.executable, then the console is NOT transient.
        #
        # For a .py file, it is a bit more complicated, but in most cases if the
        # console title contains the name of the .py file, the console is NOT a
        # transient console.
        if getattr(sys, 'frozen', False):
            if console_title != sys.executable:
                return WFKStatuses.NO_TRANSIENT_FROZEN
        elif Path(console_title).name.lower() != PYTHON_LAUNCHER.name.lower():
            return WFKStatuses.NO_TRANSIENT_PYTHON

        sys.stdout.flush()
        sys.stdout.write(_Messages.PRESS_ANY_KEY)
        sys.stdout.flush()
        getch()
        return WFKStatuses.WAIT_FOR_KEYPRESS


# pylint: disable-next=unused-variable
def get_credentials(credentials_path: Path = DEFAULT_CREDENTIALS_FILE) -> dict[str, Any] | None:
    """Get credentials for current user, from the file at credentials_path.

    If credentials_path if not provided as argument, a default path is used.

    No matter the actual syntax of the file, which may change in the future, the
    credentials are returned as a simple two-levels dictionary. The first level
    are the different sections, intended to group credentials. The second level
    are the credentials themselves. They are accessed by credential identifier
    and returned as strings.

    If credentials file cannot be read or has syntax problems, None is returned.
    """
    try:
        with credentials_path.open('rb') as credentials_file:
            return tomllib.load(credentials_file)
    except (OSError, tomllib.TOMLDecodeError):
        return None


# Module desired side-effects.
sys.excepthook = excepthook
logging.basicConfig(level=logging.NOTSET, format='%(message)s', datefmt=TIMESTAMP_FORMAT, force=True)
logging.setLoggerClass(_CustomLogger)
logger: _CustomLogger = cast('_CustomLogger', logging.getLogger(PROGRAM_NAME))
# Reconfigure standard output streams so they use UTF-8 encoding even if
# they are redirected to a file when running the application from a shell.
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    cast('TextIOWrapper', sys.stdout).reconfigure(encoding=UTF8)
if sys.stderr and hasattr(sys.stdout, 'reconfigure'):
    cast('TextIOWrapper', sys.stderr).reconfigure(encoding=UTF8)


def demo() -> None:
    """Show module constants."""
    sys.stdout.write(f'Legion module version {LEGION_VERSION}\n\n')
    sys.stdout.write(_Messages.DEMO_TIMESTAMP.format(timestamp()))
    constants = {k: v for k, v in globals().items() if k.isupper() and not k.startswith('_')}
    width = max(len(name) for name in constants) + 1
    for constant, value in constants.items():
        sys.stdout.write(_Messages.DEMO_CONSTANT.format(constant, width, value))
    sys.stdout.flush()

if __name__ == '__main__':
    demo()

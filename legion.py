#! /usr/bin/env python3
"""
Legion.

“What is your name?”
“My name is Legion,” he replied, “for we are many.”

Since the module is many, it's legion.

cspell: ignore osascript oserror munge
"""
import atexit
from enum import StrEnum
from errno import errorcode
import logging
from logging.config import dictConfig
from os import environ, system
from pathlib import Path
import subprocess
import sys
from textwrap import dedent
from time import strftime
import traceback as tb

if sys.platform == 'win32':
    from enum import auto, IntEnum  # pylint: disable=ungrouped-imports
    from ctypes import byref, c_uint, create_unicode_buffer, windll
    from ctypes.wintypes import MAX_PATH as MAX_PATH_LEN
    from msvcrt import get_osfhandle, getch


__all__ = []  # pylint: disable=unused-variable


def _get_desktop_path():
    """Get the path of the desktop directory depending on the platform."""
    home_path = Path.home()
    desktop_basename = 'Desktop'

    if sys.platform == 'win32':
        hwnd = 0
        desktop_csidl = 0
        access_token = 0
        shgfp_type_current = 0
        flags = shgfp_type_current
        buffer = create_unicode_buffer(MAX_PATH_LEN)
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


def _get_program_path():
    """Get the full, resolved path of the currently executing program."""
    program_path = None
    try:
        if getattr(sys, 'frozen', False):
            program_path = sys.executable
        else:
            # This method is not failproof, because there are probably situations
            # where the '__file__' attribute of module '__main__' won't exist but
            # there's some filename involved.
            #
            # If one of those situations arise, the code will be modified accordingly.
            program_path = sys.modules['__main__'].__file__
        return Path(program_path).resolve()
    except AttributeError:
        return program_path


class _Config():  # pylint: disable=too-few-public-methods
    """Module configuration values."""
    DESKTOP_BASENAME = 'Desktop'
    FALLBACK_PROGRAM_NAME = '<stdin>'

    ERROR_MARKER = '*** '
    ERROR_PAYLOAD_INDENT = len(ERROR_MARKER)

    TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'

    LOGGING_CONSOLE_FORMAT = '{message}'
    LOGGING_FALLBACK_FORMAT = '{message}'
    LOGGING_FORMAT_STYLE = '{'
    LOGGING_INDENTCHAR = ' '
    LOGGING_DEBUGFILE_FORMAT = '{asctime}.{msecs:04.0f} {levelname}| {funcName}() {message}'
    LOGGING_LOGFILE_FORMAT = '{asctime} {message}'

    if sys.platform == 'win32':
        PYTHON_LAUNCHER = 'py.exe'
        MB_ICONWARNING = 0x30
        MB_OK = 0


class Constants():  # pylint: disable=too-few-public-methods
    """Exportable constants."""
    DESKTOP_PATH = _get_desktop_path()
    PROGRAM_PATH = _get_program_path()
    PROGRAM_NAME = PROGRAM_PATH.stem if PROGRAM_PATH else _Config.FALLBACK_PROGRAM_NAME

    ARROW_R = '⟶'
    ARROW_L = '⟵'

    UTF8 = 'utf-8'


class Messages(StrEnum):
    """Module messages."""
    ERROR_HEADER = f'\n{_Config.ERROR_MARKER}Error in {Constants.PROGRAM_NAME}.'
    ERROR_DETAILS_HEADING = '\nAdditional error information:'
    ERROR_DETAILS_PREAMBLE = '│ '
    ERROR_DETAILS_TAIL = '╰'

    UNEXPECTED_OSERROR = 'Unexpected OSError.'
    OSERROR_DETAILS = dedent('''
         type = {}
        errno = {}
     winerror = {}
     strerror = {}
     filename = {}
    filename2 = {}
    ''').strip('\n')
    OSERROR_DETAIL_NA = 'N/A'
    UNHANDLED_EXCEPTION = 'Unhandled exception.'
    EXCEPTION_DETAILS = 'type = {}\nvalue = {}\nargs: {}'
    EXCEPTION_DETAILS_ARG = '\n  [{}] {}'
    TRACEBACK_HEADER = '\n\ntraceback:\n{}'
    TRACEBACK_FRAME_HEADER = '▸ {}\n'
    TRACEBACK_FRAME_LINE = '  {}, {}: {}\n'
    TRACEBACK_TOPLEVEL_FRAME = '<module>'
    UNKNOWN_ERRNO = 'unknown'
    ERRDIALOG_TITLE = 'Unexpected error in {Constants.PROGRAM_NAME}'

    PRESS_ANY_KEY_MESSAGE = '\nPress any key to continue...'

    DEMO_TIMESTAMP = 'Timestamp is {}\n'
    DEMO_CONSTANT = '{:┄<{}}⟶ ⟦{}⟧'


# Reconfigure standard output streams so they use UTF-8 encoding even if
# they are redirected to a file when running the application from a shell.
if sys.stdout:
    sys.stdout.reconfigure(encoding=Constants.UTF8)
if sys.stderr:
    sys.stderr.reconfigure(encoding=Constants.UTF8)


def error(message, details=''):
    """Helper for preprocessing error messages."""
    message = str(message)
    details = str(details)
    logging.indent(0)
    logging.error(Messages.ERROR_HEADER)
    logging.indent(_Config.ERROR_PAYLOAD_INDENT)
    logging.error(message)
    if details := details.strip():
        logging.error(Messages.ERROR_DETAILS_HEADING)
        logging.error('\n'.join(f'{Messages.ERROR_DETAILS_PREAMBLE}{line}' for line in details.split('\n')))
        logging.error(Messages.ERROR_DETAILS_TAIL)
    logging.indent(0)


def excepthook(exc_type, exc_value, exc_traceback):  # pylint: disable=unused-variable
    """Handle unhandled exceptions, default exception hook."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    if isinstance(exc_value, OSError):
        message = Messages.UNEXPECTED_OSERROR
        details = Messages.OSERROR_DETAILS.format(
            exc_type.__name__,
            Messages.OSERROR_DETAIL_NA if exc_value.errno is None else errorcode[exc_value.errno],
            Messages.OSERROR_DETAIL_NA if exc_value.winerror is None else exc_value.winerror,
            exc_value.strerror,
            Messages.OSERROR_DETAIL_NA if exc_value.filename is None else exc_value.filename,
            Messages.OSERROR_DETAIL_NA if exc_value.filename2 is None else exc_value.filename2,
        )
    else:
        message = Messages.UNHANDLED_EXCEPTION
        args = ''
        for arg in exc_value.args:
            args += Messages.EXCEPTION_DETAILS_ARG.format(type(arg).__name__, arg)
        details = Messages.EXCEPTION_DETAILS.format(exc_type.__name__, str(exc_value), args)
    current_filename = None
    traceback = ''
    for frame in tb.extract_tb(exc_traceback):
        if current_filename != frame.filename:
            traceback += Messages.TRACEBACK_FRAME_HEADER.format(frame.filename)
            current_filename = frame.filename
        frame.name = Constants.PROGRAM_NAME if frame.name == Messages.TRACEBACK_TOPLEVEL_FRAME else frame.name
        traceback += Messages.TRACEBACK_FRAME_LINE.format(frame.lineno, frame.name, frame.line)
    details += Messages.TRACEBACK_HEADER.format(traceback) if traceback else ''
    error(message, details)

    # Just in case there is NOT a working console or logging system,
    # the error message is also shown in a popup window so the end
    # user is aware of the problem even with uninformative details.
    if sys.platform == 'win32':
        windll.user32.MessageBoxW(None, message, Messages.ERRDIALOG_TITLE, _Config.MB_ICONWARNING | _Config.MB_OK)
    if sys.platform == 'darwin':
        script = f'display dialog "{message}" with title "{Messages.ERRDIALOG_TITLE}" with icon caution buttons "OK"'
        system(f'''osascript -e '{script}' >/dev/null''')
sys.excepthook = excepthook


def munge_oserror(exception):  # pylint: disable=unused-variable
    """
    Munge information for OSError exception.

    Process the exception object for OSError exceptions (and its subclasses),
    and build a string usable as output message for end users, containing the
    actual OSError subclass which was raised, the error code, the error string
    and the filenames involved.

    For convenience, the munged (stringified) exception information is returned
    as a tuple. The first element is the generated string, and the rest of the
    elements used for building the string are also returned, just in case the
    caller wants to format the string in another way. The additional elements
    are strings containing the actual OSError subclass which was raised, the
    errno code, the winerror code (which will be None if it is not used by the
    current platform), the error message and the two filenames, filename and
    filename2. Except maybe for the error message, any member of the tuple can
    be None if not defined by the actual error which raised the exception.

    IMPORTANT: the returned string DOESN'T END IN A PERIOD. The caller must add
    the proper punctuation needed when outputting the message.

    Examples:
        # Using the provided string.
        import legion
        try:
            [...]
        except OSError as exc:
            sys.exit(legion.munge_oserror(exc)[0])
        ··································································
        # Using the convenience tuple.
        import legion
        try:
            [...]
        except OSError as exc:
            message = '{}: [{}] {} "{}"'.format(*legion.munge_oserror(exc)[1:4])
            sys.exit(message)
    """
    err_type = type(exception).__name__
    err_errno = None
    err_winerror = None

    try:
        err_winerror = f'WinError{exception.winerror}'
    except AttributeError:
        pass
    try:
        err_errno = errorcode[exception.errno]
    except KeyError:
        pass

    err_codestring = f'{err_errno}/{err_winerror}' if err_errno and err_winerror else err_errno or err_winerror
    message = f'{err_type}{f" [{err_codestring}]" if err_codestring else ""}: {exception.strerror}'

    if exception.filename:
        message += f" ('{exception.filename}'"
        if exception.filename2:
            message += f" -> '{exception.filename2}'"
        message += ')'

    return (message, err_type, err_errno, err_winerror, exception.strerror, exception.filename, exception.filename2)


def prettyprint_oserror(reason, exc):  # pylint: disable=unused-variable
    """Generates a pretty-printed OSError message using reason and exc information."""
    err_errno, err_winerror, error_message, filename = munge_oserror(exc)[2:6]
    err_code = f'{err_errno}/{err_winerror}' if err_errno and err_winerror else err_errno or err_winerror
    err_code = f'{f" [{err_code}]" if err_code else " desconocido"}'

    logging.error("%s%s %s '%s'.\n", Messages.ERROR_HEADER, err_code, reason, filename)
    logging.indent(_Config.ERROR_PAYLOAD_INDENT)
    logging.error('%s.', error_message)


def timestamp():  # pylint: disable=unused-variable
    """Produce a timestamp string from current local date and time."""
    return strftime(_Config.TIMESTAMP_FORMAT)


def run(*command, **subprocess_args):  # pylint: disable=unused-variable
    """
    Run command, using subprocess_args as arguments. This is just a helper for
    subprocess.run() to make such calls more convenient by providing a set of
    defaults for the arguments.

    For that reason, the keyword arguments accepted in subprocess_args and the
    return value for this function are the exact same ones accepted and returned
    by subprocess.run() function itself.
    """
    subprocess_args = {
        'capture_output': True,
        'check': False,
        'creationflags': 0,
        'errors': 'replace',
        'text': True,
    } | subprocess_args

    if sys.platform == 'win32':
        subprocess_args['creationflags'] |= subprocess.CREATE_NO_WINDOW

    # pylint: disable-next=subprocess-run-check
    return subprocess.run(*command, **subprocess_args)


# Needed for having VERY basic logging when setup_logging() is not used.
logging.basicConfig(
    level=logging.NOTSET,
    style=_Config.LOGGING_FORMAT_STYLE,
    format=_Config.LOGGING_FALLBACK_FORMAT,
    force=True
)
logging.indent = lambda level=None: None
logging.dedent = lambda level=None: None


def setup_logging(debugfile=None, logfile=None, console=True):  # pylint: disable=unused-variable
    """
    Set up logging system, disabling all existing loggers.

    With the current configuration ALL logging messages are sent to debugfile
    and logging.INFO messages are sent to logfile, timestamped.

    In addition to that, and if console is True (the default), all logging.INFO
    messages are sent to the console too, but without a timestamp.

    If debugfile or logfile are None, the corresponding files are not created
    and no logging message will go there. In this case, if console is False,
    NO LOGGING OUTPUT WILL BE PRODUCED AT ALL.
    """
    class CustomFormatter(logging.Formatter):
        """Simple custom formatter for logging messages."""
        def format(self, record):
            """
            Format multiline records so they look like multiple records.
            Indent message according to current indentation level.
            """
            message = super().format(record)
            preamble, message = message.partition(record.message)[:2]
            return '\n'.join(f'{preamble}{record.indent}{line}' for line in message.split('\n'))

    logging_configuration = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'debugfile_formatter': {
                '()': CustomFormatter,
                'style': _Config.LOGGING_FORMAT_STYLE,
                'format': _Config.LOGGING_DEBUGFILE_FORMAT,
                'datefmt': _Config.TIMESTAMP_FORMAT
            },
            'logfile_formatter': {
                '()': CustomFormatter,
                'style': _Config.LOGGING_FORMAT_STYLE,
                'format': _Config.LOGGING_LOGFILE_FORMAT,
                'datefmt': _Config.TIMESTAMP_FORMAT
            },
            'console_formatter': {
                '()': CustomFormatter,
                'style': _Config.LOGGING_FORMAT_STYLE,
                'format': _Config.LOGGING_CONSOLE_FORMAT,
            },
        },
        'filters': {
            'debugfile_filter': {'()': lambda: lambda record: record.msg.strip() and record.levelno > logging.NOTSET},
            'logfile_filter': {'()': lambda: lambda record: record.msg.strip() and record.levelno >= logging.INFO},
            'stdout_filter': {'()': lambda: lambda record: record.msg.strip() and record.levelno == logging.INFO},
            'stderr_filter': {'()': lambda: lambda record: record.msg.strip() and record.levelno > logging.INFO},
        },
        'handlers': {},
        'loggers': {
            '': {
                'level': logging.NOTSET,
                'handlers': [],
                'propagate': False,
            },
        },
    }

    if debugfile:
        logging_configuration['handlers']['debugfile'] = {
            'level': logging.NOTSET,
            'formatter': 'debugfile_formatter',
            'filters': ['debugfile_filter'],
            'class': logging.FileHandler,
            'filename': debugfile,
            'mode': 'w',
            'encoding': Constants.UTF8
        }
        logging_configuration['loggers']['']['handlers'].append('debugfile')

    if logfile:
        logging_configuration['handlers']['logfile'] = {
            'level': logging.NOTSET,
            'formatter': 'logfile_formatter',
            'filters': ['logfile_filter'],
            'class': logging.FileHandler,
            'filename': logfile,
            'mode': 'w',
            'encoding': Constants.UTF8
        }
        logging_configuration['loggers']['']['handlers'].append('logfile')

    if console:
        logging_configuration['handlers']['stdout_handler'] = {
            'level': logging.NOTSET,
            'formatter': 'console_formatter',
            'filters': ['stdout_filter'],
            'class': logging.StreamHandler,
            'stream': sys.stdout,
        }
        logging_configuration['loggers']['']['handlers'].append('stdout_handler')
        logging_configuration['handlers']['stderr_handler'] = {
            'level': logging.NOTSET,
            'formatter': 'console_formatter',
            'filters': ['stderr_filter'],
            'class': logging.StreamHandler,
            'stream': sys.stderr,
        }
        logging_configuration['loggers']['']['handlers'].append('stderr_handler')

    dictConfig(logging_configuration)

    setattr(logging.getLogger(), 'indentlevel', 0)
    current_factory = logging.getLogRecordFactory()
    levelname_template = f'{{:{len(max(logging.getLevelNamesMapping(), key=len))}}}'
    def record_factory(*args, **kwargs):
        """LogRecord factory which supports indentation."""
        record = current_factory(*args, **kwargs)
        record.indent = _Config.LOGGING_INDENTCHAR * logging.getLogger().indentlevel
        record.levelname = levelname_template.format(record.levelname)
        return record
    logging.setLogRecordFactory(record_factory)

    increase_indent_symbol = '+'
    decrease_indent_symbol = '-'
    def set_indent_level(level):
        """
        Set current indentation level.

        If level is increase_indent_symbol, current indentation level is increased.
        If level is decrease_indent_symbol, current indentation level is decreased.
        For any other value, indentation level is set to the provided value.
        """
        if level == '+':
            logging.getLogger().indentlevel += 1
            return
        if level == '-':
            logging.getLogger().indentlevel -= 1
            return
        logging.getLogger().indentlevel = level
    # Both logging.indent() and logging.dedent() support a parameter specifying an
    # exact FINAL indentation level, not an indentation increment/decrement!
    # These two helpers are provided in order to improve readability, since the
    # set_logging_indent_level() function can be used directly.
    logging.indent = lambda level=None: set_indent_level(increase_indent_symbol if level is None else level)
    logging.dedent = lambda level=None: set_indent_level(decrease_indent_symbol if level is None else level)


if sys.platform == 'win32':
    class WFKStatuses(IntEnum):
        """Return statuses for wait_for_keypress()."""
        NO_WIN32 = auto()
        NO_CONSOLE_ATTACHED = auto()
        NO_CONSOLE_TITLE = auto()
        NO_TRANSIENT_FROZEN = auto()
        NO_TRANSIENT_PYTHON = auto()
        WAIT_FOR_KEYPRESS = auto()

    @atexit.register
    def wait_for_keypress():  # pylint: disable=unused-variable,too-many-return-statements
        """Wait for a keypress to continue if sys.stdout is a real console AND the console is transient."""
        if sys.platform != 'win32':
            return WFKStatuses.NO_WIN32

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
        buffer_size = MAX_PATH_LEN + 1
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
        elif Path(console_title).name.lower() != _Config.PYTHON_LAUNCHER.lower():
            return WFKStatuses.NO_TRANSIENT_PYTHON

        print(Messages.PRESS_ANY_KEY_MESSAGE, end='', flush=True)
        getch()
        return WFKStatuses.WAIT_FOR_KEYPRESS


if __name__ == '__main__':
    print(Messages.DEMO_TIMESTAMP.format(timestamp()))

    constants = {k:v for k,v in vars(Constants).items() if not k.startswith('__')}
    width = max(len(name) for name in constants) + 1
    for constant, value in constants.items():
        print(Messages.DEMO_CONSTANT.format(constant, width, value))

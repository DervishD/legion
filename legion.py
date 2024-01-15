#! /usr/bin/env python3
"""
Legion.

“What is your name?”
“My name is Legion,” he replied, “for we are many.”

Since the module is many, it's legion.

cspell: ignore osascript oserror munge
"""
import errno
import logging
from logging.config import dictConfig
import os
import os.path
import subprocess
import sys
import time
import traceback

if sys.platform == 'win32':
    from enum import auto, IntEnum
    from ctypes import byref, c_uint, create_unicode_buffer, windll
    from ctypes.wintypes import MAX_PATH as MAX_PATH_LEN
    from msvcrt import get_osfhandle, getch


__all__ = []  # pylint: disable=unused-variable


# Some constants used to prevent mistyping.
UTF8 = 'utf-8'


class Config():  # pylint: disable=too-few-public-methods
    """Application configuration values."""
    FALLBACK_PROGRAM_NAME = '<stdin>'

    TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'

    LOGGING_INDENTCHAR = ' '
    LOGGING_FORMAT_STYLE = '{'
    LOGGING_FALLBACK_FORMAT = '{message}'
    LOGGING_LOGFILE_FORMAT = '{asctime}.{msecs:04.0f} {levelname}| {funcName}() {message}'
    LOGGING_OUTPUTFILE_FORMAT = '{asctime} {message}'
    LOGGING_CONSOLE_FORMAT = '{message}'

    if sys.platform == 'win32':
        PYTHON_LAUNCHER = 'py.exe'
        MB_ICONWARNING = 0x30
        MB_OK = 0


# This heavily depends on the operating system used, not only the platform but
# the particular operating system. For example, under Linux this depends of the
# particular distribution, and under Windows this depends on the version and
# the end-user language, as the path may be localized.
#
# The default is just to expand to a home directory, which is far from perfect
# but works in all platforms, according to the Python Standard Library manual.
HOME_PATH = os.path.expanduser('~')


def __get_desktop_path():  # pylint: disable=unused-variable
    """Get the path of the desktop directory depending on the platform."""
    desktop_basename = 'Desktop'

    if sys.platform == 'win32':
        hwnd = 0
        desktop_csidl = 0
        access_token = 0
        shgfp_type_current = 0
        flags = shgfp_type_current
        buffer = create_unicode_buffer(MAX_PATH_LEN)
        windll.shell32.SHGetFolderPathW(hwnd, desktop_csidl, access_token, flags, buffer)
        return buffer.value

    if sys.platform == 'darwin':
        return os.path.join(HOME_PATH, desktop_basename)

    if sys.platform.startswith('linux'):
        try:
            return os.environ['XDG_DESKTOP_DIR']
        except KeyError:
            return os.path.join(HOME_PATH, desktop_basename)

    return HOME_PATH

DESKTOP_PATH = __get_desktop_path()


try:
    if getattr(sys, 'frozen', False):
        PROGRAM_PATH = sys.executable
    else:
        # This method is not failproof, because there are probably situations
        # where the '__file__' attribute of module '__main__' won't exist but
        # there's some filename involved.
        #
        # If one of those situations arise, the code will be modified accordingly.
        PROGRAM_PATH = sys.modules['__main__'].__file__
    PROGRAM_PATH = os.path.realpath(PROGRAM_PATH)
    PROGRAM_NAME = os.path.splitext(os.path.basename(PROGRAM_PATH))[0]
except AttributeError:
    PROGRAM_PATH = None
    PROGRAM_NAME = Config.FALLBACK_PROGRAM_NAME


def excepthook(exc_type, exc_value, exc_traceback):  # pylint: disable=unused-variable
    """Handle unhandled exceptions, default exception hook."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    message = (
        f'Unhandled exception {exc_type.__name__}.\n'
        f'at file {exc_traceback.tb_frame.f_code.co_filename}, line {exc_traceback.tb_lineno}\n\n'
        f'''{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)).replace('"', '')}'''
    )
    logging.error('\n%s', message)
    title = f'Unexpected error in {PROGRAM_NAME}'

    # Just in case there is NOT a working console or logging system,
    # the error message is also shown in a popup window so the end
    # user is aware of the problem even with uninformative details.
    if sys.platform == 'win32':
        windll.user32.MessageBoxW(None, message, title, Config.MB_ICONWARNING | Config.MB_OK)
    if sys.platform == 'darwin':
        script = f'display dialog "{message}" with title "{title}" with icon caution buttons "OK"'
        os.system(f'''osascript -e '{script}' >/dev/null''')


def fix_output_streams():  # pylint: disable=unused-variable
    """
    Reconfigure standard output streams so they use UTF-8 encoding even if
    they are redirected to a file when running the program from a shell.
    """
    if sys.stdout:
        sys.stdout.reconfigure(encoding=UTF8)
    if sys.stderr:
        sys.stderr.reconfigure(encoding=UTF8)


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
    caller wants to format the string in another way. These additional elements
    are strings containing the actual OSError subclass which was raised, the
    error code, the error message and the two filenames, filename and filename2
    (if any, None otherwise).

    By default the error code, both in the generated string and in the munged
    information tuple, is the errno code as a string, except on Windows where if
    WinError exists it takes precedence over errno.

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
    errortype = type(exception).__name__
    errorcode = None

    try:
        if exception.winerror:
            errorcode = f'WinError {exception.winerror}'
    except AttributeError:
        pass

    if errorcode is None:
        errorcode = errno.errorcode[exception.errno]

    message = f'{errortype} [{errorcode}]: {exception.strerror}'

    if exception.filename:
        message += f" ('{exception.filename}'"
        if exception.filename2:
            message += f" -> '{exception.filename2}'"
        message += ')'

    return (message, errortype, errorcode, exception.strerror, exception.filename, exception.filename2)


def timestamp():  # pylint: disable=unused-variable
    """Produce a timestamp string from current local date and time."""
    return time.strftime(Config.TIMESTAMP_FORMAT)


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
        'check': False,
        'capture_output': True,
        'text': True,
        'errors': 'replace',
        'creationflags': subprocess.CREATE_NO_WINDOW,
    } | subprocess_args

    # pylint: disable-next=subprocess-run-check
    return subprocess.run(*command, **subprocess_args)


# Needed for having VERY basic logging when setup_logging() is not used.
logging.basicConfig(
    level=logging.NOTSET,
    style=Config.LOGGING_FORMAT_STYLE,
    format=Config.LOGGING_FALLBACK_FORMAT,
    force=True
)
logging.indent = lambda level=None: None
logging.dedent = lambda level=None: None


def setup_logging(logfile=None, outputfile=None, console=True):  # pylint: disable=unused-variable
    """
    Set up logging system, disabling all existing loggers.

    With the current configuration ALL logging messages are sent to logfile
    and logging.INFO messages are sent to outputfile, timestamped.

    In addition to that, and if console is True (the default), logging.INFO
    messages are sent to the console too, but without a timestamp.

    If logfile or outputfile are None, the corresponding files are not created
    and no logging message will go there. In this case, if console is False, NO
    LOGGING OUTPUT WILL BE PRODUCED AT ALL.
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
            return '\n'.join([f'{preamble}{record.indent}{line.strip()}'.rstrip() for line in message.splitlines()])

    logging_configuration = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'logfile_formatter': {
                '()': CustomFormatter,
                'style': Config.LOGGING_FORMAT_STYLE,
                'format': Config.LOGGING_LOGFILE_FORMAT,
                'datefmt': Config.TIMESTAMP_FORMAT
            },
            'outputfile_formatter': {
                '()': CustomFormatter,
                'style': Config.LOGGING_FORMAT_STYLE,
                'format': Config.LOGGING_OUTPUTFILE_FORMAT,
                'datefmt': Config.TIMESTAMP_FORMAT
            },
            'console_formatter': {
                '()': CustomFormatter,
                'style': Config.LOGGING_FORMAT_STYLE,
                'format': Config.LOGGING_CONSOLE_FORMAT,
            },
        },
        'filters': {
            'logfile_filter': {'()': lambda: lambda record: record.msg.strip() and record.levelno > logging.NOTSET},
            'outputfile_filter': {'()': lambda: lambda record: record.msg.strip() and record.levelno >= logging.INFO},
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

    if logfile:
        logging_configuration['handlers']['logfile'] = {
            'level': logging.NOTSET,
            'formatter': 'logfile_formatter',
            'filters': ['logfile_filter'],
            'class': logging.FileHandler,
            'filename': logfile,
            'mode': 'w',
            'encoding': UTF8
        }
        logging_configuration['loggers']['']['handlers'].append('logfile')

    if outputfile:
        logging_configuration['handlers']['outputfile'] = {
            'level': logging.NOTSET,
            'formatter': 'outputfile_formatter',
            'filters': ['outputfile_filter'],
            'class': logging.FileHandler,
            'filename': outputfile,
            'mode': 'w',
            'encoding': UTF8
        }
        logging_configuration['loggers']['']['handlers'].append('outputfile')

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
        record.indent = Config.LOGGING_INDENTCHAR * logging.getLogger().indentlevel
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
        IMPORTED = auto()
        NO_CONSOLE_ATTACHED = auto()
        NO_CONSOLE_TITLE = auto()
        NO_TRANSIENT_FROZEN = auto()
        NO_TRANSIENT_PYTHON = auto()
        WAIT_FOR_KEYPRESS = auto()

    def wait_for_keypress():  # pylint: disable=unused-variable,too-many-return-statements
        """Wait for a keypress to continue if sys.stdout is a real console AND the console is transient."""
        if sys.platform != 'win32':
            return WFKStatuses.NO_WIN32

        if __name__ != '__main__':
            return WFKStatuses.IMPORTED

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
        elif os.path.basename(console_title).lower() != Config.PYTHON_LAUNCHER:
            return WFKStatuses.NO_TRANSIENT_PYTHON

        print('\nPress any key to continue...', end='', flush=True)
        getch()
        return WFKStatuses.WAIT_FOR_KEYPRESS


if __name__ == '__main__':
    print(f'Desktop path: [{DESKTOP_PATH}]')
    print(f'Program path: [{PROGRAM_PATH}]')
    print(f'Program name: [{PROGRAM_NAME}]')
    print(f'Timestamp is {timestamp()}')

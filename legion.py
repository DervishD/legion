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
    import ctypes
    import ctypes.wintypes


__all__ = (  # pylint: disable=unused-variable
    'DESKTOP_PATH',
    'PROGRAM_NAME',
    'PROGRAM_PATH',
    'UTF8',
    'excepthook',
    'munge_oserror',
    'setup_logging',
    'fix_output_streams',
    'run'
)


# Some constants used to prevent mistyping.
UTF8 = 'utf-8'
MB_ICONWARNING = 0x30
MB_OK = 0


# This heavily depends on the operating system used, not only the platform but
# the particular operating system. For example, under Linux this depends of the
# particular distribution, and under Windows this depends on the version and
# the end-user language, as the path may be localized.
#
# The default is just to expand to a home directory, which is far from perfect
# but works in all platforms, according to the Python Standard Library manual.
DESKTOP_PATH = os.path.expanduser('~')


if sys.platform == 'win32':
    DESKTOP_PATH = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(0, 0, 0, 0, DESKTOP_PATH)
    DESKTOP_PATH = DESKTOP_PATH.value


if sys.platform == 'darwin':
    DESKTOP_PATH = os.path.join(os.path.expanduser('~'), 'Desktop')


if sys.platform.startswith('linux'):
    try:
        DESKTOP_PATH = os.environ['XDG_DESKTOP_DIR']
    except KeyError:
        DESKTOP_PATH = os.path.join(os.path.expanduser('~'), 'Desktop')


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
    PROGRAM_NAME = '<stdin>'


def excepthook(exc_type, exc_value, exc_traceback):
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
        ctypes.windll.user32.MessageBoxW(None, message, title, MB_ICONWARNING | MB_OK)
    if sys.platform == 'darwin':
        script = f'display dialog "{message}" with title "{title}" with icon caution buttons "OK"'
        os.system(f'''osascript -e '{script}' >/dev/null''')


def munge_oserror(exception):
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


def timestamp():
    """Produce a timestamp string from current local date and time."""
    return time.strftime('%Y%m%d_%H%M%S')


def setup_logging(logfile=None, outputfile=None, console=True):
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
    class MultilineFormatter(logging.Formatter):
        """Simple multiline formatter for logging messages."""

        def format(self, record):
            """Format multiline records so they look like multiple records."""
            message = super().format(record)

            if not record.message.strip():
                return message.strip()

            preamble = message.split(record.message)[0]
            return f'\n{preamble}'.join([line.rstrip() for line in message.splitlines() if line.strip()])

    logging_configuration = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'detailed': {
                '()': MultilineFormatter,
                'style': '{',
                'format': '{asctime}.{msecs:04.0f} [{levelname}] {funcName}() {message}',
                'datefmt': '%Y%m%d_%H%M%S'
            },
            'simple': {
                '()': MultilineFormatter,
                'style': '{',
                'format': '{asctime} {message}',
                'datefmt': '%Y%m%d_%H%M%S'
            },
            'console': {
                'style': '{',
                'format': '{message}',
            },
        },
        'filters': {
            'output': {'()': lambda: lambda log_record: log_record.levelno == logging.INFO},
            'console': {'()': lambda: lambda log_record: log_record.levelno in (logging.ERROR, logging.INFO)}
        },
        'handlers': {},
        'loggers': {
            '': {
                'level': 'NOTSET',
                'handlers': [],
                'propagate': False,
            },
        },
    }

    if logfile:
        logging_configuration['handlers']['logfile'] = {
            'level': 'NOTSET',
            'formatter': 'detailed',
            'class': 'logging.FileHandler',
            'filename': logfile,
            'mode': 'w',
            'encoding': 'utf8'
        }
        logging_configuration['loggers']['']['handlers'].append('logfile')

    if outputfile:
        logging_configuration['handlers']['outputfile'] = {
            'level': 'NOTSET',
            'formatter': 'simple',
            'filters': ['output'],
            'class': 'logging.FileHandler',
            'filename': outputfile,
            'mode': 'w',
            'encoding': 'utf8'
        }
        logging_configuration['loggers']['']['handlers'].append('outputfile')

    if console:
        logging_configuration['handlers']['console'] = {
            'level': 'NOTSET',
            'formatter': 'console',
            'filters': ['console'],
            'class': 'logging.StreamHandler',
        }
        logging_configuration['loggers']['']['handlers'].append('console')

    dictConfig(logging_configuration)


def fix_output_streams():
    """
    Reconfigure standard output streams so they use UTF-8 encoding even if
    they are redirected to a file when running the program from a shell.
    """
    if sys.stdout:
        sys.stdout.reconfigure(encoding=UTF8)
    if sys.stderr:
        sys.stderr.reconfigure(encoding=UTF8)


def run(*command, **subprocess_args):
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


if __name__ == '__main__':
    print(f'Desktop path: [{DESKTOP_PATH}]')
    print(f'Program path: [{PROGRAM_PATH}]')
    print(f'Program name: [{PROGRAM_NAME}]')
    print(f'Timestamp is {timestamp()}')

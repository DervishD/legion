#! /usr/bin/env python3
"""
Legion.

“What is your name?”
“My name is Legion,” he replied, “for we are many.”

Since the module is many, it's legion.
"""
import sys
import os
import os.path
import errno
import logging
from logging.config import dictConfig
import traceback
import time
if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes

# cspell: ignore osascript oserror

__all__ = (  # pylint: disable=unused-variable
    'DESKTOP_PATH',
    'PROGRAM_NAME',
    'PROGRAM_PATH',
    'excepthook',
    'munge_oserror',
    'setup_logging',
)


# Desktop path.
#
# This heavily depends on the operating system used, not only the platform but
# the particular operating system. For example, under Linux this depends of the
# particular distribution, and under Windows this depends on the version and
# the end-user language, as the path may be localized.
#
# The default is just to expand to a home directory, which is far from perfect
# but works in all platforms, according to the Python Standard Library manual.
DESKTOP_PATH = os.path.expanduser('~')


# On Windows it's better to use the ctypes modules.
if sys.platform == 'win32':
    DESKTOP_PATH = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(0, 0, 0, 0, DESKTOP_PATH)
    DESKTOP_PATH = DESKTOP_PATH.value


# This works for modern macOS at least.
if sys.platform == 'darwin':
    DESKTOP_PATH = os.path.join(os.path.expanduser('~'), 'Desktop')


# On Linux, if xdg-user-dirs exists, it's better to use it.
# Otherwise the same default as for macOS is used.
if sys.platform.startswith('linux'):
    try:
        DESKTOP_PATH = os.environ['XDG_DESKTOP_DIR']
    except KeyError:
        DESKTOP_PATH = os.path.join(os.path.expanduser('~'), 'Desktop')


# Current program path and name (without extension).
#
# This method is not failproof, because probably there are some situations
# where the '__file__' attribute of module '__main__' won't exist but there's
# some filename involved. If one of those situations arise, the code will be
# modified accordingly.
#
# So, this is a best-effort.
#
# PROGRAM_PATH is the canonical path for the current program.
# PROGRAM_NAME is the name for the current program, without any extension.
try:
    if getattr(sys, 'frozen', False):
        PROGRAM_PATH = sys.executable
    else:
        PROGRAM_PATH = sys.modules['__main__'].__file__
    PROGRAM_PATH = os.path.realpath(PROGRAM_PATH)
    PROGRAM_NAME = os.path.splitext(os.path.basename(PROGRAM_PATH))[0]
except AttributeError:
    PROGRAM_PATH = None
    PROGRAM_NAME = '<stdin>'


def excepthook(exc_type, exc_value, exc_traceback):
    """
    Handle unhandled exceptions, default exception hook.

    Provides a default exception hook to assign to sys.excepthook, check the
    documentation for sys.excepthook documentation for further details.

    This module could assign the value itself,
    but explicit is better than implicit...
    It's the Tao.

    To use this function as the default exception hook, do the following:
        import sys
        import legion
        ...
        sys.excepthook = legion.excepthook
    """
    if issubclass(exc_type, KeyboardInterrupt):  # Act like a NOP if the user interrupted the program.
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    message = (
        f'Unhandled exception {exc_type.__name__}.\n'
        f'at file {exc_traceback.tb_frame.f_code.co_filename}, line {exc_traceback.tb_lineno}\n\n'
        f'''{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)).replace('"', '')}'''
    )
    # No matter what, the error message is logged.
    #
    # If there is a working logging system, the full details of the error will
    # be in a safe place for future inspection.
    #
    # Best case scenario, there is also a working console and the logging.ERROR
    # messages will be shown there, too. Worst case scenario, handled below.
    logging.error('\n%s', message)
    title = 'Unexpected error in {PROGRAM_NAME}'

    # Just in case there is NOT a working console or logging system, show the
    # message in a popup, depending on the platform, so the end user will be
    # aware of the problem even though the details may not be very readable.
    if sys.platform == 'win32':
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x30)  # 0x30 = MB_ICONWARNING | MB_OK
    if sys.platform == 'darwin':
        script = f'display dialog "{message}" with title "{title}" with icon caution buttons "OK"'
        os.system(f'''osascript -e '{script}' >/dev/null''')


def munge_oserror(exception):
    """
    Munge exception information for OSError exceptions.

    Processes the exception object for OSError exceptions (and its subclasses),
    and builds a string usable as output message for end users, containing the
    actual OSError subclass which was raised, the error code, the error string
    and the filenames involved.

    For convenience, the munged (stringified) exception information is returned
    too as a list: type, error code, error string, filename and filename2.

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

    Arguments:
        exception: The exception object to be munged.

    Returns:
        A tuple. The first element is the generated string, but for convenience
        the munged (stringified) elements used for building the string are also
        returned, just in case the caller wants to format the string in another
        way. These additional elements are strings containing the actual OSError
        subclass which was raised, the error code, the error message and the
        two filenames, filename and filename2 (if any, None otherwise).

        By default the error code, both in the generated string and in the
        munged information tuple, is the errno code as a string, except on
        Windows where if WinError exists it takes precedence over errno.

        IMPORTANT: the returned string DOESN'T END IN A PERIOD. The caller must
        add the proper punctuation needed when outputting the message.
    """
    errortype = type(exception).__name__
    errorcode = None

    # No need to test for the platform, winerror doesn't exist outside Windows.
    try:
        if exception.winerror:
            errorcode = f'WinError {exception.winerror}'
    except AttributeError:
        pass

    if errorcode is None:
        errorcode = errno.errorcode[exception.errno]

    message = f'{errortype} [{errorcode}]: {exception.strerror}'

    # Allegedly, if filename2 is non empty, filename won't be, either.
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

    With the current configuration ALL logging messages are sent to 'logfile'
    and logging.INFO messages are sent to 'outputfile', timestamped.

    In addition to that, and if 'console' is True, logging.INFO messages are
    sent to the console too, but without a timestamp.

    If 'logfile' or 'outputfile' are None, the corresponding files are not
    created and no logging message will go there. In this case, if 'console' is
    False, NO LOGGING OUTPUT WILL BE PRODUCED AT ALL.
    """
    class MultilineFormatter(logging.Formatter):
        """Simple multiline formatter for logging messages."""

        def format(self, record):
            """Format multiline records so they look like multiple records."""
            message = super().format(record)  # Default formatting first.

            # For empty messages return the message as-is, but stripped.
            if record.message.strip() == '':
                return message.strip()

            # Get the preamble so it can be reproduced on each line.
            preamble = message.split(record.message)[0]
            # Return cleaned message: no multiple newlines, no trailing spaces,
            # and the preamble is inserted at the beginning of each line.
            return f'↲\n{preamble}'.join([line.rstrip() for line in message.splitlines() if line.strip()])

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
            '': {  # root logger.
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


# These tests are a bit incomplete, but for now they'll do.
if __name__ == '__main__':
    print(f'Desktop path: [{DESKTOP_PATH}]')
    print(f'Program path: [{PROGRAM_PATH}]')
    print(f'Program name: [{PROGRAM_NAME}]')
    print(f'Timestamp is {timestamp()}')

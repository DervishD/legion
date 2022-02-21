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
    import win32con
    import win32ui
    from win32com.shell import shell, shellcon   # pylint: disable=no-name-in-module,import-error


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


# On Windows it's better to use the ctypes-based win32com.shell modules.
if sys.platform == 'win32':
    DESKTOP_PATH = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, 0, 0)


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
    PROGRAM_PATH = os.path.realpath(sys.modules['__main__'].__file__)
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
    message = f'Unhandled exception {exc_type.__name__}'
    logging.exception(message, exc_info=exc_value)
    message += '\n'
    message += 'at file {}, line {}\n\n'.format(*traceback.extract_tb(exc_traceback)[-1])
    message += ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)).replace('"', '')
    title = 'Unexpected error'
    if sys.platform == 'win32':
        win32ui.MessageBox(message, title, win32con.MB_ICONWARNING)
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
    """
    Produce a timestamp string from current local date and time.

    The current format string is YYYYMMDD_HHMMSS.
    """
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
    logging_configuration = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'detailed': {
                'style': '{',
                'format': '{asctime}.{msecs:04.0f} [{levelname}] {message}',
                'datefmt': '%Y%m%d_%H%M%S'
            },
            'simple': {
                'style': '{',
                'format': '{asctime} {message}',
                'datefmt': '%Y%m%d_%H%M%S'
            },
            'message': {
                'style': '{',
                'format': '{message}',
            },
        },
        'filters': {'output': {'()': lambda: lambda log_record: log_record.levelno == logging.INFO}},
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
            'formatter': 'message',
            'filters': ['output'],
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

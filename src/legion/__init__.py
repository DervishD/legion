#! /usr/bin/env python3
"""# legion

> 'What is your name?'<br>
> 'My name is Legion,' he replied, 'for we are many.'

Since this is many, it's *legion*. This package (currently, a single
module) contains miscellaneous functions and constants used in some of
the maintenance scripts of my private system. It is shared publicly in
case the code may be useful to others.

## Constants
{}
## Functions
{}
"""  # noqa: D400, D415
from annotationlib import Format, get_annotations
import atexit
import contextlib
from enum import StrEnum
from errno import errorcode
from inspect import getsource, signature
import logging
from logging.config import dictConfig
from os import environ
from pathlib import Path
import re
import subprocess
import sys
from textwrap import dedent
from time import strftime
import tomllib
import traceback as tb
from typing import Annotated, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from io import TextIOWrapper
    from types import TracebackType
    from typing import Any, LiteralString


__all__: list[str] = [  # pylint: disable=unused-variable  # noqa: RUF022
    'DESKTOP_PATH',
    'DEFAULT_CREDENTIALS_PATH',
    'TIMESTAMP_FORMAT',
    'ERROR_MARKER',
    'ARROW_R',
    'ARROW_L',
    'UTF8',
    'Logger',
    'excepthook',
    'munge_oserror',
    'format_oserror',
    'format_message',
    'timestamp',
    'run',
    'get_credentials',
    'get_logger',
    'wait_for_keypress',
    'docs',
]


if sys.platform == 'win32':
    from ctypes import byref, c_uint, create_unicode_buffer, windll
    from ctypes.wintypes import MAX_PATH as _MAX_PATH_LEN
    from msvcrt import get_osfhandle, getch


def _get_desktop_path() -> Path:
    """Get platform specific path for the desktop."""
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


# Exportable constants.
DESKTOP_PATH: Annotated[Path, "Path of user's desktop directory."] = _get_desktop_path()

DEFAULT_CREDENTIALS_PATH: Annotated[Path, """
Default filename used by `get_credentials()` for user credentials.
"""] = Path.home() / '.credentials'

TIMESTAMP_FORMAT: Annotated[str, '`time.strftime()` compatible format specification for timestamps.'] = '%Y%m%d_%H%M%S'
ERROR_MARKER: Annotated[str, 'Marker string prepended to error messages.'] = '*** '
ARROW_R: Annotated[str, 'Right-pointing arrow character for pretty-printing program output.'] = '⟶'
ARROW_L: Annotated[str, 'Left-pointing arrow character for pretty-printing program output.'] = '⟵'
UTF8: Annotated[str, 'Normalized name for `UTF-8` encoding.'] = 'utf-8'


_OSERROR_WINERROR_FMT = 'WinError{}'
_OSERROR_ERRORCODES_FMT = '{}/{}'
    """Module internal constants."""

    NOT_AVAILABLE = '???'

    EXCEPTHOOK_HEADING_FMT = '{} ({})'

    OSERROR_COMPACT_FMT = 'OSError [{}] {} {}.\n{}'
    OSERROR_DETAILED_FMT = dedent("""
         type = {}
        errno = {}
     winerror = {}
     strerror = {}
     filename = {}
    filename2 = {}
    """).strip('\n')
    OSERROR_WINERROR_FMT = 'WinError{}'
    OSERROR_ERRORCODES_FMT = '{}/{}'

    EXCEPTION_DETAILS_FMT = 'exc_type = {}\nexc_value = {}\nexc_args: {}'
    EXCEPTION_DETAILS_ARG_FMT = f'\n{INTERNAL_INDENTATION}[{{}}] {{}}'
    TRACEBACK_HEADER_FMT = '\n\ntraceback:\n{}'
    TRACEBACK_FRAME_HEADER_FMT = '▸ {}\n'
    TRACEBACK_FRAME_LINE_FMT = f'{INTERNAL_INDENTATION}{{}}, {{}}: {{}}\n'

    PRESS_ANY_KEY_MESSAGE = '\nPress any key to continue...'


def format_message(
    message: str = '',
    details: str = '',
    *,
    details_indent: str = ' ',
) -> str:
    """Format *message*, including *details*. Both are optional.

    The *message* is sanitized: any trailing whitespace is stripped, and
    any sequence of internal whitespace is converted to a single space.
    Leading whitespace is preserved, though.

    If *details* are provided, they are appended to *message*. A newline
    character is used as a visual separator between them if *message* is
    not empty. The lines in *detail* are indented by *details_indent*, a
    a single space by default but any string can be used.

    Multiline *details* are supported and empty lines are preserved. For
    each line trailing whitespace is stripped and leading whitespace is
    preserved. This allows to use a per-line arbitrary indentation, and
    to have visual separation from *message* by including some newline
    characters at the very beginning of *details*.
    """
    output: list[str] = []
    if message and not message.isspace():
        output.append(re.sub(r'(?<=\S)(\s+)(?=\S)', r' ', message.rstrip()))
    if details and not details.isspace():
        output.extend(f'{details_indent}{line}'.rstrip() for line in details.split('\n'))
    return '\n'.join(output)


def _stringize_exception_details(exc_type: type[BaseException], exc_value: BaseException) -> str:
    """Extract exception details as a formatted string."""
    if isinstance(exc_value, OSError):
        errno_message = _Constants.OSERROR_DETAIL_NOT_AVAILABLE
        if exc_value.errno:
            with contextlib.suppress(IndexError):
                errno_message = errorcode[exc_value.errno]
        return _Constants.OSERROR_DETAILS_FMT.format(
            exc_type.__name__,
            errno_message,
            exc_value.winerror or _Constants.OSERROR_DETAIL_NOT_AVAILABLE,
            exc_value.strerror,
            _Constants.OSERROR_DETAIL_NOT_AVAILABLE if exc_value.filename is None else exc_value.filename,
            _Constants.OSERROR_DETAIL_NOT_AVAILABLE if exc_value.filename2 is None else exc_value.filename2,
        )
    args = ''
    for arg in exc_value.args:
        args += _Constants.EXCEPTION_DETAILS_ARG_FMT.format(type(arg).__name__, arg)
    return _Constants.EXCEPTION_DETAILS_FMT.format(exc_type.__name__, str(exc_value), args)


def _stringize_traceback(exc_traceback: TracebackType | None) -> str:
    """Extract traceback as a formatted string."""
    current_frame_source_path = None
    traceback = ''
    for frame in tb.extract_tb(exc_traceback):
        if current_frame_source_path != frame.filename:
            traceback += _Constants.TRACEBACK_FRAME_HEADER_FMT.format(frame.filename)
            current_frame_source_path = frame.filename
        traceback += _Constants.TRACEBACK_FRAME_LINE_FMT.format(frame.lineno, frame.name, frame.line)
    return traceback


def excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
    *,
    unhandled_exception_heading: str = _Constants.UNHANDLED_EXCEPTION_HEADING,
    unhandled_oserror_heading: str = _Constants.UNHANDLED_OSERROR_HEADING,
) -> None:
    """Log unhandled exceptions.

    Intended to be used as default exception hook in `sys.excepthook`.

    Unhandled exceptions are logged, using the provided arguments, that
    is, the exception type (*exc_type*), its value (*exc_value*) and the
    associated traceback (*exc_traceback*).

    The formatting can be customized by using the following keyword-only
    arguments, but if not provided, default strings are used:
    - *unhandled_exception_heading*
    - *unhandled_oserror_heading*

    **NOTE**: in order to provide this formatting arguments when using
    the function as `sys.excepthook`, `functools.partial()` can be used
    to create a new function with the desired defaults, but other
    alternative mechanisms can be used as well.

    A banner is prepended to the exception information, depending on the
    type of the exception: for `OSError` exception, the banner used is
    *unhandled_oserror_heading* and for the rest of possible exceptions,
    *unhandled_exception_heading* is used.

    For `OSError` exceptions, any additional information included in the
    exception object is gathered and shown, and no traceback is logged.

    For any other exception, arguments contained in the exception object
    are included, if present, together with the traceback if available.

    `KeyboardInterrupt` exceptions are not logged. Instead, the default
    exception hook is called to preserve keyboard interrupt behavior.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    message = unhandled_oserror_heading if isinstance(exc_value, OSError) else unhandled_exception_heading
    details = _stringize_exception_details(exc_type, exc_value)
    traceback = _stringize_traceback(exc_traceback)
    details += _Constants.TRACEBACK_HEADER_FMT.format(traceback) if traceback else ''
    logger.error(format_message(message, details, details_indent=_Constants.INTERNAL_INDENTATION))


def munge_oserror(exc: OSError) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Process `OSError` exception *exc*.

    Process the `OSError` (or any of its subclasses) exception *exc* and
    return a tuple with the attributes obtained from the instance.

    The types and descriptions of the retrieved attributes are:
    - `str`: the type name of *exc*
    - `str`: the `errno` and `winerror` codes
    - `str`: the error message string, normalized (see below)
    - `str`: the first filename involved in the exception
    - `str`: the second filename involved in the exception

    The only attribute guaranteed to always exist is the first one, the
    type name of *exc*, any other may not be present and then the stored
    value will be `None`, to make easier to process the tuple in order
    to replace missing values with a marker, etc.

    **NOTE**: the `errno` and `winerror` codes are combined with a slash
    character if both are present.

    **NOTE**: the returned error message is normalized if present. The
    first letter is uppercased and a final period is added.

    **NOTE**: depending on operation which caused the exception raising,
    there may be zero, one, or two paths involved.
    """
    exc_name = type(exc).__name__
    exc_errno = None
    exc_winerror = None
    exc_errorcodes = None
    exc_message = None

    with contextlib.suppress(AttributeError):
        exc_winerror = _OSERROR_WINERROR_FMT.format(exc.winerror)

    with contextlib.suppress(KeyError):
        exc_errno = errorcode[exc.errno or -1]

    if exc_errno and exc_winerror:
        exc_errorcodes = _OSERROR_ERRORCODES_FMT.format(exc_errno, exc_winerror)
    exc_errorcodes = exc_errorcodes or exc_errno or exc_winerror or None

    if exc.strerror:
        exc_message = f'{exc.strerror[0].upper()}{exc.strerror[1:].rstrip('.')}.'

    return exc_name, exc_errorcodes, exc_message, exc.filename, exc.filename2


def format_oserror(context: str, exc: OSError) -> str:
    """Stringify `OSError` exception *exc* using *context*.

    *context* is typically used to indicate what exactly was the caller
    doing when the exception was raised.
    """
    errorcodes, message, path1, path2 = munge_oserror(exc)[1:]

    paths = f"'{path1}'{f" {ARROW_R} '{path2}'" if path2 else ''}"
    return _Constants.OSERROR_COMPACT_FMT.format(errorcodes, context, paths, message)


def timestamp() -> str:
    """Produce a timestamp string from current local date and time."""
    return strftime(TIMESTAMP_FORMAT)


def run(command: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:  # noqa: ANN401
    """Run *command* with convenient defaults.

    Run *command*, using *kwargs* as arguments. Just a simple helper for
    `subprocess.run()` that provides convenient defaults.

    For that reason, the keyword arguments accepted in *kwargs* and the
    return value are the same ones used by `subprocess.run()` itself.
    """
    kwargs.setdefault('capture_output', True)
    kwargs.setdefault('check', False)

    if kwargs.get('capture_output'):
        kwargs.setdefault('text', True)
        kwargs.setdefault('errors', 'replace')

    if sys.platform == 'win32' and 'creationflags' not in kwargs:
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    # pylint: disable=subprocess-run-check
    return cast('subprocess.CompletedProcess[str]', subprocess.run(command, **kwargs))  # noqa: S603, PLW1510


def get_credentials(credentials_path: Path = DEFAULT_CREDENTIALS_PATH) -> dict[str, Any] | None:
    """Read credentials from *credentials_path*.

    If *credentials_path* is not provided a default path is used. To be
    precise, the value of `DEFAULT_CREDENTIALS_PATH`.

    The credentials are returned as a simple dictionary. The dictionary
    has two levels: the first one groups credentials into sections, and
    the second contains the actual `key-value` pairs.

    Each credential is a `key-value` string pair, where the `key` is an
    identifier for the credential, and the `value` is the corresponding
    credential.

    If *credentials_path* cannot be read, or has syntax problems, `None`
    is returned. If it is empty, an empty dictionary is returned.
    """
    try:
        with credentials_path.open('rb') as credentials_file:
            return tomllib.load(credentials_file)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def get_logger(name: str) -> Logger:
    """Get an instance of `legion.Logger` with the specified *name*.

    Unlike `logging.getLogger()`, the argument is **not** optional, so
    the root logger is **never** returned.

    This function temporarily registers `legion.Logger` as the default
    logger class, so the returned logger type is always guaranteed to be
    `legion.Logger`, no matter what other logger classes are registered.

    This is a convenience function to avoid having to register the class
    by hand, instantiante the logger, restore the previous class, etc.
    """
    previous = logging.getLoggerClass()
    logging.setLoggerClass(Logger)
    try:
        return cast('Logger', logging.getLogger(name))
    finally:
        logging.setLoggerClass(previous)


if sys.platform == 'win32':
    def _has_attached_console() -> bool:
        """Predicate for `wait_for_keypress()`.

        Return `True` if there is a real console attached to the file
        descriptor of the `sys.stdout` file object, `False` otherwise.
        """
        # Since 'sys.stdout.isatty()' returns 'True' under Windows when
        # the 'sys.stdout' stream is redirected to 'NUL', another check,
        # a bit more complicated, is needed here. The test below has
        # been adapted from https://stackoverflow.com/a/33168697
        return windll.kernel32.GetConsoleMode(get_osfhandle(sys.stdout.fileno()), byref(c_uint()))


    def _is_attached_console_transient() -> bool:
        """Predicate for `wait_for_keypress()`.

        Return `True` if the console which is attached to `sys.stdout`
        is actually transient.
        """
        # Determining if a console is transient is not easy as there is
        # no bulletproof method available for every possible situation.
        #
        # There are TWO main runtime scenarios to consider, though: one
        # is a frozen executable and the other is a `.py` file. In both
        # cases the console title has to be obtained first.
        #
        # If the console title cannot be determined, then consider that
        # the console is NOT transient.
        buffer_size = _MAX_PATH_LEN + 1
        console_title = create_unicode_buffer(buffer_size)
        if not windll.kernel32.GetConsoleTitleW(console_title, buffer_size):
            return False
        # For a frozen executable, if the console title is not equal to
        # `sys.executable`, then the console is NOT transient.
        #
        # For a `.py` file, this is more complicated, but in most cases
        # if the console title contains the name of the `.py` file, the
        # console is NOT transient.
        if getattr(sys, 'frozen', False):
            if console_title.value != sys.executable:
                return False
        elif Path(sys.argv[0]).name in console_title.value:
            return False
        return True


    def wait_for_keypress(prompt: str = _Constants.PRESS_ANY_KEY_MESSAGE) -> None:
        """Wait for a keypress to continue in particular circumstances.

        If `sys.stdout` is attached to a transient console, the function
        prints a *prompt* message indicating that the program is paused
        until a key is pressed. If no *prompt* is provided as argument,
        a default string (in English) is used instead.

        It is a good idea to include a leading new line character in the
        *prompt* message to ensure it is clearly separated from previous
        output from the program.

        **NOTE**: there is no standard method of knowing if a console is
        transient or not, so determining console transience is entirely
        based on heuristics.

        **NOTE**: is up to the importer to register this function with
        `atexit.register()`, to call it explicitly, or to use it only if
        the importer is running as a script instead of being imported.
        """
        if _has_attached_console() and _is_attached_console_transient():
            sys.stdout.write(prompt)
            sys.stdout.flush()
            getch()
else:
    def wait_for_keypress(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Stub for platforms where this function is not implemented."""
        raise NotImplementedError



class Logger(logging.Logger):
    """Augmented functionality logger.

    Drop-in replacement for `logging.Logger` with indentation support,
    multiline records and a simple but powerful configuration helper.

    Example usage:
    ```python
    import logging
    import legion

    # Option 1: Replace the default Logger globally.
    # Using `logging.setLoggerClass()` affects *all* subsequent
    # `logging.getLogger()` calls!
    logging.setLoggerClass(legion.Logger)
    logger = logging.getLogger(__name__)

    # Option 2: Use `legion` provided shortcut to get a logger directly.
    logger = legion.getlogger(__name__)

    # Then configure the logger with default or custom settings:
    logger.config()  # Check method documentation below for details.

    ```

    The differences from `logging.Logger` are in the following methods:
    """

    __INCREASE_INDENT_SYMBOL = '+'
    __DECREASE_INDENT_SYMBOL = '-'
    __INDENT_CHAR = ' '
    __FORMAT_STYLE = '{'
    __LONG_FORMAT = '{{asctime}}.{{msecs:04.0f}} {{levelname:{levelname_max_width}}} | {{funcName}}() {{message}}'
    __SHORT_FORMAT = '{asctime} {message}'
    __CONSOLE_FORMAT = '{message}'

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        """Initialize logger with a *name* and an optional *level*."""
        super().__init__(name, level)
        self.indent_level: int = 0
        self.indentation = ''

    def makeRecord(self, *args: Any, **kwargs: Any) -> logging.LogRecord:  # noqa: ANN401, N802
        """Create a new logging record with indentation.

        Used internally by logger objects, can be called manually, too.
        """
        record = super().makeRecord(*args, **kwargs)
        record.msg = '\n'.join(f'{self.indentation}{line}'.rstrip() for line in record.msg.split('\n'))
        return record

    def __set_indent_level(self, level: int | LiteralString) -> None:
        """Set current logging indentation to *level*.

        If *level* is:
            - `INCREASE_INDENT_SYMBOL` string, indentation is increased
            - `DECREASE_INDENT_SYMBOL` string, indentation is decreased
            - Any integer `>=0`, indentation is set to that value

        For any other value, `ValueError` is raised.

        Not for public usage, use `self.set_indent(level)` instead.
        """
        if level == self.__INCREASE_INDENT_SYMBOL:
            self.indent_level += 1
        elif level == self.__DECREASE_INDENT_SYMBOL:
            self.indent_level = max(0, self.indent_level - 1)
        elif isinstance(level, int) and level >= 0:
            self.indent_level = level
        else:
            raise ValueError(level)
        self.indentation = self.__INDENT_CHAR * self.indent_level

    def set_indent(self, level: int) -> None:
        """Set current logging indentation to *level*.

        *level* can be any positive integer or zero.

        For any other value, `ValueError` is raised.
        """
        self.__set_indent_level(level)

    def indent(self) -> None:
        """Increment current logging indentation level."""
        self.__set_indent_level(self.__INCREASE_INDENT_SYMBOL)

    def dedent(self) -> None:
        """Decrement current logging indentation level."""
        self.__set_indent_level(self.__DECREASE_INDENT_SYMBOL)

    def config(self,
        full_log_output: str | Path | None = None,
        main_log_output: str | Path | None = None,
        console: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """Configure logger.

        With the default configuration, the behavior of the logger is as
        follows:
        - **File logging**
            - *full_log_output*: receives *all* messages in detailed
            format (including a timestamp and some debugging info).
            - *main_log_output*: receives messages with severity
            `logging.INFO` or higher, with a simpler format but also
            timestamped.
            - If a file path is `None`, it is not created.
        - **Console logging** (if *console* is `True`):
            - No timestamps are included in the messages.
            - Messages with severity of exactly `logging.INFO` go to the
            standard output stream.
            - Messages with severity of `logging.WARNING` or higher go
            to the standard error stream.
        - If all file paths are `None` and *console* is `False`,
            **NO LOGGING OUTPUT IS PRODUCED AT ALL**.
        """
        class _MultilineRecordFormatter(logging.Formatter):
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

        if full_log_output:
            levelname_max_len = len(max(logging.getLevelNamesMapping(), key=len))
            formatters['full_log_formatter'] = {
                '()': _MultilineRecordFormatter,
                'style': self.__FORMAT_STYLE,
                'format': self.__LONG_FORMAT.format(levelname_max_width=levelname_max_len),
                'datefmt': TIMESTAMP_FORMAT,
            }
            handlers['full_log_handler'] = {
                'level': logging.NOTSET,
                'formatter': 'full_log_formatter',
                'class': logging.FileHandler,
                'filename': full_log_output,
                'mode': 'w',
                'encoding': UTF8,
            }

        if main_log_output:
            formatters['main_log_formatter'] = {
                '()': _MultilineRecordFormatter,
                'style': self.__FORMAT_STYLE,
                'format': self.__SHORT_FORMAT,
                'datefmt': TIMESTAMP_FORMAT,
            }
            handlers['main_log_handler'] = {
                'level': logging.INFO,
                'formatter': 'main_log_formatter',
                'class': logging.FileHandler,
                'filename': main_log_output,
                'mode': 'w',
                'encoding': UTF8,
            }

        if console:
            def console_filter(record: logging.LogRecord) -> bool:
                """Filter records for StreamHandler objects."""
                return record.levelno == logging.INFO

            formatters['console_formatter'] = {
                '()': _MultilineRecordFormatter,
                'style': self.__FORMAT_STYLE,
                'format': self.__CONSOLE_FORMAT,
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


# Module desired side-effects.
sys.excepthook = excepthook
logging.basicConfig(level=logging.NOTSET, format='%(message)s', datefmt=TIMESTAMP_FORMAT, force=True)

# Reconfigure standard output streams so they use UTF-8 encoding even if
# they are redirected to a file when running the program from a shell.
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    cast('TextIOWrapper', sys.stdout).reconfigure(encoding=UTF8)
if sys.stderr and hasattr(sys.stdout, 'reconfigure'):
    cast('TextIOWrapper', sys.stderr).reconfigure(encoding=UTF8)


def _indent_markdown(markdown: str) -> str:
    """Indent all lines in *text_block* by 4 spaces.

    The indentation is four spaces as per markdown specification.aces.

    Lines which only contain whitespace after indenting are stripped.
    """
    return '\n'.join(f'{' ' * 4}{line}'.rstrip() for line in markdown.splitlines())


def _unwrap_markdown(markdown: str) -> str:
    """Unwrap *markdown* formatted text.

    Remove line breaks from *markdown*, preserving Markdown formatting
    where possible, including lists, hard line breaks, paragraphs, etc.
    """
    unwrapped: list[str] = []
    paragraph = ''
    last_indent = 0

    for line in markdown.splitlines():
        stripped_line = line.rstrip()
        current_indent = len(line) - len(stripped_line)

        if not stripped_line:
            paragraph = f'{paragraph}{'\n' if paragraph else ''}'
            unwrapped.append(paragraph)
            paragraph = ''
        elif stripped_line.endswith('<br>'):
            paragraph = f'{f'{paragraph}\n' if paragraph else ''}{stripped_line.replace('<br>', '\\')}'
            unwrapped.append(paragraph)
            paragraph = ''
        elif stripped_line.lstrip().startswith('- '):
            unwrapped.append(paragraph)
            paragraph = stripped_line
        elif stripped_line.startswith(('# ', '## ', '> ')):
            paragraph = f'{paragraph}{'\n' if paragraph else ''}{stripped_line}'
            unwrapped.append(paragraph)
            paragraph = ''
        elif current_indent != last_indent:
            unwrapped.append(paragraph)
            paragraph = stripped_line
            last_indent = current_indent
        elif paragraph:
            paragraph += f'{' ' if paragraph else ''}{stripped_line.lstrip()}'
        else:
            paragraph = stripped_line

    if paragraph:
        unwrapped.append(paragraph)

    return '\n'.join(unwrapped)


def _get_docs_for_function(name: str) -> str:
    """Get documentation for function *name*."""
    instance_name, _, function_name = name.partition('.')
    func: Callable[..., Any] = getattr(globals()[instance_name], function_name) if function_name else globals()[name]

    docstring = func.__doc__ or ''
    doc_fragment = f'`{name}('
    function_signature = signature(func, annotation_format=Format.STRING)

    paramstrings: list[str] = []
    add_positional_only_separator = False
    add_keyword_only_separator = True
    for parameter in function_signature.parameters.values():
        paramstring = parameter.name
        paramstring += f': {parameter.annotation}' if parameter.annotation != parameter.empty else ''

        if parameter.kind == parameter.POSITIONAL_ONLY:
            add_positional_only_separator = True
        elif add_positional_only_separator:
            # Non-positional-only parameter after positional-only parameters, add separator.
            paramstrings.append(f'`{_indent_markdown('/')}')
            add_positional_only_separator = False
        if parameter.kind == parameter.VAR_POSITIONAL:
            # *args-like parameter, no need to add '*' as separator for keyword-only parameters.
            add_keyword_only_separator = False
        elif parameter.kind == parameter.KEYWORD_ONLY and add_keyword_only_separator:
            # Keyword-only parameter and no *args-like parameter before, add separator.
            paramstrings.append(f'`{_indent_markdown('*')}')
            add_keyword_only_separator = False

        if paramstring != 'self':
            paramstrings.append(f'`{_indent_markdown(paramstring)}')

    if paramstrings:
        doc_fragment += f'`\\\n{',`\\\n'.join(paramstrings)}`\\\n`'

    doc_fragment += f') -> {function_signature.return_annotation}`\\\n'
    doc_fragment += _unwrap_markdown(docstring)

    return doc_fragment


def _get_docs_for_constant(name: str) -> str:
    """Get documentation for constant *name*."""
    if name not in (annotations := get_annotations(sys.modules[__name__])):
        return f'`{name}`'

    annotation = annotations[name]
    module = str(annotation.__origin__.__module__).replace('builtins', '').replace('__main__', '')
    qualname = str(annotation.__origin__.__qualname__)
    docstring = '\n'.join(annotation.__metadata__)
    type_annotation = '' if qualname.startswith('_') else f'{module}{'.' if module else ''}{qualname}'

    doc_fragment = f'`{name}{': ' if type_annotation else ''}{type_annotation}`\\\n'
    doc_fragment += f'{_unwrap_markdown(docstring.strip())}'
    obj = globals()[name]
    if obj and obj.__class__.__module__ == __name__:
        extra_docstrings: list[str] = []

        for attribute_name, attribute_object in obj.__class__.__dict__.items():
            if attribute_name.startswith('_') or not callable(attribute_object):
                continue
            method_name = f'{name}.{attribute_name}'
            attribute_docs = _indent_markdown(_get_docs_for_function(method_name)).lstrip()
            extra_docstrings.append(f'- {attribute_docs}\n')

        if extra_docstrings:
            doc_fragment = f'{doc_fragment.rstrip('.')}:\n{''.join(sorted(extra_docstrings))}'

    return doc_fragment


def docs() -> str:
    """Generate documentation for the module.

    Return a Markdown-formatted string containing the documentation for
    the module/package.
    """
    if __doc__ is None:
        return ''

    doc_fragments_for_constants: list[str] = []
    doc_fragments_for_functions: list[str] = []
    for name in __all__:
        obj = globals()[name]
        if isfunction(obj):
            destination = doc_fragments_for_functions
            doc_fragment = _get_docs_for_function(name)
        else:
            destination = doc_fragments_for_constants
            doc_fragment = _get_docs_for_constant(name)
        destination.append(f'- {_indent_markdown(doc_fragment).lstrip()}\n')

    docs_for_constants = ''.join(sorted(doc_fragments_for_constants))
    docs_for_functions = ''.join(sorted(doc_fragments_for_functions))

    return _unwrap_markdown(__doc__).format(docs_for_constants, docs_for_functions)

#! /usr/bin/env python3
"""# legion

> 'What is your name?'<br>
> 'My name is Legion,' he replied, 'for we are many.'

Since this is many, it's *legion*. This package (currently, a single
module) contains miscellaneous functions and constants used in some of
the maintenance scripts of my private system. It is shared publicly in
case the code may be useful to others.

## Constants
{docs_for_constants}
## Classes
{docs_for_classes}
## Functions
{docs_for_functions}
"""  # noqa: D400, D415
from annotationlib import get_annotations
import ast
import contextlib
from errno import errorcode
from inspect import getsource
import linecache
import logging
from logging.config import dictConfig
from os import environ
from pathlib import Path
import re
import subprocess
import sys
from textwrap import indent
from time import strftime
import tomllib
import traceback as tb
from typing import Annotated, cast, TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from io import TextIOWrapper
    from types import TracebackType
    from typing import Any, LiteralString


__all__: list[str] = [  # pylint: disable=unused-variable
    'ARROW_L',
    'ARROW_R',
    'DEFAULT_CREDENTIALS_PATH',
    'DESKTOP_PATH',
    'ERROR_MARKER',
    'TIMESTAMP_FORMAT',
    'UTF8',
    'Logger',
    'docs',
    'excepthook',
    'format_message',
    'format_oserror',
    'get_credentials',
    'get_logger',
    'munge_oserror',
    'run',
    'timestamp',
    'wait_for_keypress',
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


_DEFAULT_EXCEPTHOOK_HEADING = 'Unhandled exception'
_DEFAULT_WAIT_FOR_KEYPRESS_PROMPT = '\nPress any key to continue...'

_EXCEPTHOOK_HEADING_TEMPLATE = '{} ({})'
_EXCEPTHOOK_BLOCK_SEPARATOR = '\n\n'

_EXCEPTION_ATTRIBUTE_TEMPLATE = f'{{:<{{}}}}  {ARROW_R}  {{}}'
_EXCEPTION_ATTRIBUTE_NOT_AVAILABLE = '???'

_OSERROR_WITH_CONTEXT_TEMPLATE = 'OSError [{}] {} {}.\n{}.'
_OSERROR_WINERROR_TEMPLATE = 'WinError{}'
_OSERROR_ERRORCODES_TEMPLATE = '{}/{}'
_OSERROR_ATTRIBUTE_LABELS = ('errcodes', 'strerror', 'filename1', 'filename2')

_TRACEBACK_FRAME_HEADING_MARKER = f'{ARROW_R} '
_TRACEBACK_FRAME_HEADING_TEMPLATE = f'{_TRACEBACK_FRAME_HEADING_MARKER}{{}}\n'
_TRACEBACK_FRAME_LOCATION_TEMPLATE = f'{' ' * len(_TRACEBACK_FRAME_HEADING_MARKER)}{{}}, {{}}: {{}}\n'

_MARKDOWN_INDENTATION = ' ' * 4


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
        output.append(indent(details, details_indent))
    return '\n'.join(output)


def _format_exception_details(exc: BaseException) -> str:
    """Extract exception details as a formatted string."""
    if isinstance(exc, OSError):
        labels = _OSERROR_ATTRIBUTE_LABELS
        values = munge_oserror(exc)[1:]
    else:
        labels = tuple(type(value).__name__ for value in exc.args)
        values = exc.args
    label_maxlen = max((len(label) for label in labels), default=0)

    output: list[str] = []
    for label, value in zip(labels, values, strict=True):
        processed_value = _EXCEPTION_ATTRIBUTE_NOT_AVAILABLE if value is None else value
        processed_value = processed_value.strip('.') if label == 'strerror' else processed_value
        output.append(_EXCEPTION_ATTRIBUTE_TEMPLATE.format(label, label_maxlen, processed_value))

    return '\n'.join(output)


def _format_traceback(exc_traceback: TracebackType | None) -> str:
    """Extract traceback as a formatted string."""
    output = ''

    current_frame_source_path = None
    for frame in tb.extract_tb(exc_traceback):
        if current_frame_source_path != frame.filename:
            output += _TRACEBACK_FRAME_HEADING_TEMPLATE.format(frame.filename)
            current_frame_source_path = frame.filename
        source_lines: list[str] = []
        if frame.lineno:
            source_lines = linecache.getlines(frame.filename)[frame.lineno-1:frame.end_lineno]
        else:
            source_lines = [frame.line or '']

        source_lines = [line.strip() for line in source_lines]
        output += _TRACEBACK_FRAME_LOCATION_TEMPLATE.format(frame.lineno, frame.name, ''.join(source_lines))
    return output.strip()


def excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
    *,
    heading: str = _DEFAULT_EXCEPTHOOK_HEADING,
) -> None:
    """Log diagnostic information about unhandled exceptions.

    Intended for use as the default exception hook via `sys.excepthook`,
    either directly, via `functools.partial()`, or through an equivalent
    mechanism.

    Diagnostic information about the unhandled exception is logged using
    *exc_type*, *exc_value*, and *exc_traceback* arguments.

    The output is formatted as follows: the first line consists of the
    *heading* and the exception type name in parentheses. Any remaining
    diagnostic information is logged on subsequent lines as needed, and
    with a default indentation. If no *heading* is provided, a default
    string is used instead.

    Additional information is taken from the tuple of arguments passed
    to the exception constructor, with one entry per line including the
    type and the value for each argument.

    For `OSError` (and derived) exceptions these arguments are not very
    informative, so the specific attributes of this exception family are
    logged instead, one per line.

    Finally, a traceback is included if available.

    `KeyboardInterrupt` exceptions are not logged. Instead, the default
    exception hook is called to preserve keyboard interrupt behavior.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    exc = exc_value.__cause__ or (exc_value if exc_value.__suppress_context__ else exc_value.__context__ or exc_value)
    formatted_heading = _EXCEPTHOOK_HEADING_TEMPLATE.format(heading, type(exc).__name__)

    formatted_details = [_format_exception_details(exc)]
    formatted_details.append(_format_traceback(exc_traceback))
    formatted_details.append(_format_traceback(exc.__traceback__) if exc.__traceback__ != exc_traceback else '')

    logger = get_logger(__name__)
    logger.error(format_message(formatted_heading, _EXCEPTHOOK_BLOCK_SEPARATOR.join(formatted_details)))


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
    first letter is uppercased and the final period (if any), removed.

    **NOTE**: depending on operation which caused the exception raising,
    there may be zero, one, or two paths involved.
    """
    exc_name = type(exc).__name__
    exc_errno = None
    exc_winerror = None
    exc_errorcodes = None
    exc_message = None

    with contextlib.suppress(AttributeError):
        exc_winerror = _OSERROR_WINERROR_TEMPLATE.format(exc.winerror)

    with contextlib.suppress(KeyError):
        exc_errno = errorcode[exc.errno or -1]

    if exc_errno and exc_winerror:
        exc_errorcodes = _OSERROR_ERRORCODES_TEMPLATE.format(exc_errno, exc_winerror)
    exc_errorcodes = exc_errorcodes or exc_errno or exc_winerror or None

    if exc.strerror:
        exc_message = f'{exc.strerror[0].upper()}{exc.strerror[1:].rstrip('.')}'

    return exc_name, exc_errorcodes, exc_message, exc.filename, exc.filename2


def format_oserror(context: str, exc: OSError) -> str:
    """Stringify `OSError` exception *exc* using *context*.

    *context* is typically used to indicate what exactly was the caller
    doing when the exception was raised.
    """
    errorcodes, message, path1, path2 = munge_oserror(exc)[1:]

    paths = f"'{path1}'{f" {ARROW_R} '{path2}'" if path2 else ''}"
    return _OSERROR_WITH_CONTEXT_TEMPLATE.format(errorcodes, context, paths, message)


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


    def wait_for_keypress(prompt: str = _DEFAULT_WAIT_FOR_KEYPRESS_PROMPT) -> None:
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

    LEVELNAME_MAX_LEN = len(max(logging.getLevelNamesMapping(), key=len))
    LEVELNAME_SEPARATOR = ' | '
    __INCREASE_INDENT_SYMBOL = '+'
    __DECREASE_INDENT_SYMBOL = '-'
    __INDENT_CHAR = ' '
    __FORMAT_STYLE = '{'
    __SHORT_FORMAT = '{asctime} {message}'
    __CONSOLE_FORMAT = '{message}'
    __LONG_FORMAT = (
        '{asctime}.{msecs:04.0f} '
        f'{{levelname:{LEVELNAME_MAX_LEN}}}'
        f'{LEVELNAME_SEPARATOR}'
        '{funcName}() {message}'
    )

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

        This is an **authoritative, application-level setup call** that
        replaces any existing root logger configuration. It should be
        called **once and early** in the application lifecycle, before
        any other logging setup has been established.

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
                '': {
                    'level': logging.NOTSET,
                    'handlers': [],
                },
            },
        }

        formatters = {}
        handlers = {}

        if full_log_output:
            formatters['full_log_formatter'] = {
                '()': _MultilineRecordFormatter,
                'style': self.__FORMAT_STYLE,
                'format': self.__LONG_FORMAT,
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

        if not handlers:
            handlers['null_handler'] = {'class': logging.NullHandler}

        logging_configuration['formatters'] = formatters
        logging_configuration['handlers'] = handlers
        logging_configuration['loggers']['']['handlers'] = handlers.keys()
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

    The indentation is four spaces as per markdown specification

    Lines which only contain whitespace after indenting are stripped.
    """
    return '\n'.join(f'{_MARKDOWN_INDENTATION}{line}'.rstrip() for line in markdown.splitlines())


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


class DocstringVisitor(ast.NodeVisitor):
    """AST visitor for getting docstrings."""

    def __init__(self) -> None:
        """Initialize."""
        self.import_mapping: dict[str, str] = {}
        self.within_class_definition = False
        self.within_function_signature = False
        self.annotations = get_annotations(sys.modules[__name__])
        self.doc_fragments_for_functions: list[str] = []
        self.doc_fragments_for_constants: list[str] = []
        self.doc_fragments_for_classes: list[str] = []

    def _qualify_names(self, string: str) -> str:
        """Replace all bare names with fully qualified names."""
        pattern = rf'\b({'|'.join(re.escape(alias) for alias in self.import_mapping)})\b'
        return re.sub(pattern, lambda match: self.import_mapping[match.group(1)], string)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # pylint: disable=invalid-name
        """Visit Import node."""
        if not node.module:
            return
        for alias in node.names:
            self.import_mapping[alias.asname or alias.name] = f'{node.module}.{alias.asname or alias.name}'

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # pylint: disable=invalid-name
        """Visit FunctionDef node."""
        name = node.name

        if name.startswith('__') or (name not in __all__ and not self.within_class_definition):
            return

        doc_fragment = f'`{name}('

        arguments = [f'`{_indent_markdown(arg)}' for arg in ast.unparse(node.args).split(', ') if arg and arg != 'self']
        doc_fragment += f'`\\\n{',`\\\n'.join(arguments)}`\\\n`' if arguments else ''

        return_annotation = ast.unparse(node.returns) if node.returns is not None else ''
        doc_fragment += f'){f' -> {return_annotation}' if return_annotation else ''}`\\\n'

        doc_fragment = self._qualify_names(doc_fragment).replace('=', ' = ')

        docstring = ast.get_docstring(node)
        doc_fragment += _unwrap_markdown(docstring) if docstring else ''

        doc_fragment = f'- {_indent_markdown(doc_fragment).lstrip()}\n'

        if self.within_class_definition:
            self.doc_fragments_for_classes.append(f'{_indent_markdown(doc_fragment)}\n')
        else:
            self.doc_fragments_for_functions.append(doc_fragment)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # pylint: disable=invalid-name
        """Visit ClassDef node."""
        name = node.name

        if name not in __all__:
            return

        docstring = ast.get_docstring(node)
        doc_fragment = f'- `{name}`{f'\\\n{_indent_markdown(docstring)}' if docstring else ''}\n'
        self.doc_fragments_for_classes.append(doc_fragment)

        self.within_class_definition = True
        self.generic_visit(node)
        self.within_class_definition = False

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # pylint: disable=invalid-name
        """Visit AnnAssign node."""
        if not isinstance(node.target, ast.Name):
            return

        name = node.target.id

        if name not in __all__:
            return

        annotation = self.annotations[name]

        module = str(annotation.__origin__.__module__).replace('builtins', '').replace('__main__', '')
        qualname = str(annotation.__origin__.__qualname__)
        type_annotation = '' if qualname.startswith('_') else f'{module}{'.' if module else ''}{qualname}'

        docstring = '\n'.join(annotation.__metadata__).strip()

        doc_fragment = f'`{name}: {type_annotation}`\\\n{docstring}'

        self.doc_fragments_for_constants.append(f'- {_indent_markdown(doc_fragment).lstrip()}\n')


def docs() -> str:
    """Generate documentation for the module.

    Return a Markdown-formatted string containing the documentation for
    the module/package.
    """
    if __doc__ is None:
        return ''

    visitor = DocstringVisitor()
    visitor.visit(ast.parse(getsource(sys.modules[__name__])))

    return _unwrap_markdown(__doc__).format(
        docs_for_constants=''.join(visitor.doc_fragments_for_constants),
        docs_for_classes=''.join(visitor.doc_fragments_for_classes),
        docs_for_functions=''.join(visitor.doc_fragments_for_functions),
    )

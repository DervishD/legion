"""# legion

> 'What is your name?'<br>
> 'My name is Legion,' he replied, 'for we are many.'

Since this is many, it's *legion*. This package (currently, a single
module) contains miscellaneous functions and constants used in some of
the maintenance scripts of my private system. It is shared publicly in
case the code may be useful to others.

## API reference
{}
"""  # noqa: D400, D415
import ast
import contextlib
from errno import errorcode
import functools
from inspect import getsource
import linecache
import logging
from logging.config import dictConfig
from os import environ, fsdecode
from pathlib import Path
import re
import subprocess
import sys
from textwrap import indent
from time import strftime
import tomllib
import traceback as tb
from typing import cast, TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from io import TextIOWrapper
    from types import TracebackType
    from typing import Any, LiteralString


__all__: list[str] = [  # pylint: disable=unused-variable
    'Logger',
    'docs',
    'ensure_utf8_output',
    'excepthook',
    'format_message',
    'format_oserror',
    'get_credentials',
    'get_desktop_path',
    'get_logger',
    'munge_oserror',
    'run',
    'timestamp',
    'wait_for_keypress',
]


if sys.platform == 'win32':
    from ctypes import byref, c_uint, create_unicode_buffer, Structure, windll
    from ctypes.wintypes import BYTE, DWORD, LPWSTR, MAX_PATH as _MAX_PATH_LEN, WORD
    from msvcrt import get_osfhandle, getch


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
    LEVELNAME_SEPARATOR = '|'
    __INCREASE_INDENT_SYMBOL = '+'
    __DECREASE_INDENT_SYMBOL = '-'
    __INDENT_CHAR = ' '
    __FORMAT_STYLE = '{'
    __TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'
    __SHORT_FORMAT = '{asctime} {message}'
    __CONSOLE_FORMAT = '{message}'
    __LONG_FORMAT = (
        '{asctime}.{msecs:04.0f} '
        f'{{levelname:{LEVELNAME_MAX_LEN}}} '
        f'{LEVELNAME_SEPARATOR} '
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

        class _LateBindingStreamHandler(logging.StreamHandler[TextIO]):
            """Late-bindable `StreamHandler`."""  # noqa: D204
            def __init__(self, stream_name: str) -> None:
                """."""
                super().__init__()
                self.stream_name = stream_name
            @property
            def stream(self) -> TextIO:
                """Get the current stream object."""
                return cast('TextIO', getattr(sys, self.stream_name))
            @stream.setter
            def stream(self, _: TextIO) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
                pass

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
                'datefmt': self.__TIMESTAMP_FORMAT,
            }
            handlers['full_log_handler'] = {
                'level': logging.NOTSET,
                'formatter': 'full_log_formatter',
                'class': logging.FileHandler,
                'filename': full_log_output,
                'mode': 'w',
                'encoding': 'utf-8',
            }

        if main_log_output:
            formatters['main_log_formatter'] = {
                '()': _MultilineRecordFormatter,
                'style': self.__FORMAT_STYLE,
                'format': self.__SHORT_FORMAT,
                'datefmt': self.__TIMESTAMP_FORMAT,
            }
            handlers['main_log_handler'] = {
                'level': logging.INFO,
                'formatter': 'main_log_formatter',
                'class': logging.FileHandler,
                'filename': main_log_output,
                'mode': 'w',
                'encoding': 'utf-8',
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
                '()': _LateBindingStreamHandler,
                'stream_name': 'stdout',
            }
            handlers['stderr_handler'] = {
                'level': logging.WARNING,
                'formatter': 'console_formatter',
                '()': _LateBindingStreamHandler,
                'stream_name': 'stderr',
            }

        if not handlers:
            handlers['null_handler'] = {'class': logging.NullHandler}

        logging_configuration['formatters'] = formatters
        logging_configuration['handlers'] = handlers
        logging_configuration['loggers']['']['handlers'] = handlers.keys()
        dictConfig(logging_configuration)


def _indent_markdown(markdown: str) -> str:
    """Indent all lines in *text_block* by 4 spaces.

    The indentation is four spaces as per Markdown specification.

    Lines which only contain whitespace after indenting are stripped.
    """
    indentation = ' ' * 4  # Markdown spec requirement.
    return '\n'.join(f'{indentation}{line}'.rstrip() for line in markdown.splitlines())


def _unwrap_markdown(markdown: str) -> str:
    """Unwrap *markdown* formatted text.

    Remove line breaks from *markdown*, preserving Markdown formatting
    where possible, including lists, hard line breaks, paragraphs, etc.
    """
    unwrapped: list[str] = []
    paragraph = ''
    for line in markdown.splitlines():
        rstripped_line = line.rstrip()

        if not rstripped_line:
            paragraph = f'{paragraph}{'\n' if paragraph else ''}'
            unwrapped.append(paragraph)
            paragraph = ''
        elif rstripped_line.endswith('<br>'):
            paragraph = f'{f'{paragraph}\n' if paragraph else ''}{rstripped_line.replace('<br>', '\\')}'
            unwrapped.append(paragraph)
            paragraph = ''
        elif rstripped_line.lstrip().startswith('- '):
            unwrapped.append(paragraph)
            paragraph = rstripped_line
        elif rstripped_line.startswith(('# ', '## ', '> ')):
            paragraph = f'{paragraph}{'\n' if paragraph else ''}{rstripped_line}'
            unwrapped.append(paragraph)
            paragraph = ''
        elif paragraph:
            paragraph += f'{' ' if paragraph else ''}{rstripped_line.lstrip()}'
        else:
            paragraph = rstripped_line
    unwrapped.append(paragraph)

    return '\n'.join(unwrapped).rstrip()


class _DocstringVisitor(ast.NodeVisitor):
    """AST visitor for getting docstrings."""

    def __init__(self) -> None:
        """Initialize."""
        self._import_mapping: dict[str, str] = {}
        self._within_class_definition = False
        self._function_fragments: list[str] = []
        self._class_fragments: list[str] = []

    def get_full_docs(self) -> str:
        """Get the full docs so far retrieved."""
        return ''.join(self._class_fragments + self._function_fragments)

    def _qualify_names(self, string: str) -> str:
        """Replace all bare names with fully qualified names."""
        pattern = rf'\b({'|'.join(re.escape(alias) for alias in self._import_mapping)})\b'
        return re.sub(pattern, lambda match: self._import_mapping[match.group(1)], string)

    def _format_ast_arguments(self, node: ast.arguments) -> str:
        """Format an ast.arguments *node* to Markdown."""
        markdown: list[str] = []

        def _format_ast_arg (arg_node: ast.arg | None, default_expr: ast.expr | None = None) -> str:
            if arg_node is None:
                return ''
            annotation = f': {ast.unparse(arg_node.annotation)}' if arg_node.annotation is not None else ''
            default_value = f' = {ast.unparse(default_expr)}' if default_expr is not None else ''
            return f'{arg_node.arg}{self._qualify_names(annotation + default_value)}'

        normal_args = node.posonlyargs + node.args
        normal_defaults = [None] * (len(normal_args) - len(node.defaults)) + node.defaults
        for index, item in enumerate(zip(normal_args, normal_defaults, strict=True), 1):
            markdown.append(_format_ast_arg(*item))
            if index == len(node.posonlyargs):
                markdown.append('/')  # pragma: no cover  # Until posonlyargs are used in the module.

        if node.vararg or node.kwonlyargs:
            markdown.append(f'*{_format_ast_arg(node.vararg)}')

        for arg_node, default_expr in zip(node.kwonlyargs, node.kw_defaults, strict=True):
            markdown.append(_format_ast_arg(arg_node, default_expr))

        if node.kwarg:
            markdown.append(f'**{_format_ast_arg(node.kwarg)}')

        markdown = [f'`{_indent_markdown(arg)}' for arg in markdown]
        return f'`\\\n{",`\\\n".join(markdown)}`\\\n`' if markdown else ''

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # pylint: disable=invalid-name
        """Visit Import node."""
        for alias in node.names:
            self._import_mapping[alias.asname or alias.name] = f'{node.module}.{alias.asname or alias.name}'

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # pylint: disable=invalid-name
        """Visit FunctionDef node."""
        name = node.name

        if name.startswith('__') or (name not in __all__ and not self._within_class_definition):
            return

        doc_fragment = f'`{name}('

        if self._within_class_definition:
            if node.args.posonlyargs and node.args.posonlyargs[0].arg == 'self':
                node.args.posonlyargs.pop(0)  # pragma: no cover  # Until posonlyargs are used in the module.
            elif node.args.args and node.args.args[0].arg == 'self':  # pragma: no branch
                node.args.args.pop(0)

        arguments_fragment = self._format_ast_arguments(node.args)
        return_annotation = self._qualify_names(ast.unparse(node.returns) if node.returns is not None else '')
        return_fragment = f' -> {return_annotation}' if return_annotation else ''

        doc_fragment = f'`{name}({arguments_fragment}){return_fragment}`\\\n'

        docstring = ast.get_docstring(node)
        doc_fragment += _unwrap_markdown(docstring) if docstring else ''

        doc_fragment = f'- {_indent_markdown(doc_fragment).lstrip()}\n'

        if self._within_class_definition:
            self._class_fragments.append(f'{_indent_markdown(doc_fragment)}\n')
        else:
            self._function_fragments.append(doc_fragment)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # pylint: disable=invalid-name
        """Visit ClassDef node."""
        name = node.name

        if name not in __all__:
            return

        docstring = ast.get_docstring(node)
        doc_fragment = f'- `{name}`{f'\\\n{_indent_markdown(docstring)}' if docstring else ''}\n'
        self._class_fragments.append(doc_fragment)

        self._within_class_definition = True
        self.generic_visit(node)
        self._within_class_definition = False


def docs() -> str:
    """Return this module documentation in Markdown format."""
    if __doc__ is None:  # pragma: no cover
        raise RuntimeError

    visitor = _DocstringVisitor()
    visitor.visit(ast.parse(getsource(sys.modules[__name__])))

    return _unwrap_markdown(__doc__).format(visitor.get_full_docs())


def ensure_utf8_output[**P, R](f: Callable[P, R]) -> Callable[P, R]:
    """Ensure UTF-8 encoding on output streams for the wrapped function.

    Reconfigure standard output streams so they use UTF-8 encoding even
    if they are redirected to a file when running the program from the
    command line, particularly on win32 platform, where the encoding in
    that case is locale-dependent and may not be UTF-8.
    """
    @functools.wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
            cast('TextIOWrapper', sys.stdout).reconfigure(encoding='utf-8')
        if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
            cast('TextIOWrapper', sys.stderr).reconfigure(encoding='utf-8')
        return f(*args, **kwargs)
    return wrapper


def _format_exception_details(exc: BaseException) -> str:
    """Extract exception details as a formatted string."""
    if isinstance(exc, OSError):
        munged = munge_oserror(exc)
        labels = munged.keys()
        values = munged.values()
    else:
        labels = tuple(type(value).__name__ for value in exc.args)
        values = exc.args
    label_maxlen = max((len(label) for label in labels), default=0)

    output: list[str] = []

    for label, value in zip(labels, values, strict=True):
        processed_value = (str(value).strip() if value is not None else '') or '???'
        processed_value = processed_value.strip('.') if label == 'strerror' else processed_value
        output.append(f'{label:<{label_maxlen}}  ⟶  {processed_value}')

    return '\n'.join(output)


def _format_traceback(exc_traceback: TracebackType | None) -> str:
    """Extract traceback as a formatted string."""
    output: list[str] = []
    marker = '⟶ '
    padding = ' ' * len(marker)

    current_frame_source_path = None
    for frame in tb.extract_tb(exc_traceback):
        if current_frame_source_path != frame.filename:
            output.append(f'{marker}{frame.filename}')
            current_frame_source_path = frame.filename
        source = ''
        if frame.lineno:
            source_lines = linecache.getlines(frame.filename)[frame.lineno-1:frame.end_lineno]
            source = ''.join([line.strip() for line in source_lines])
        output.append(f'{padding}{frame.lineno}, {frame.name}: {source or frame.line or ''}')
    return '\n'.join(output)


def excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
    *,
    heading: str = 'Unhandled exception',
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
    formatted_heading = f'{heading} ({type(exc).__name__})'

    formatted_details = [_format_exception_details(exc)]
    formatted_details.append(_format_traceback(exc_traceback))
    formatted_details.extend([_format_traceback(exc.__traceback__)] if exc.__traceback__ != exc_traceback else [])

    logger = get_logger(__name__)
    logger.error(format_message(formatted_heading, '\n\n'.join(formatted_details)))


def format_message(
    heading: str,
    message: str,
    *,
    indentation: str = ' ',
) -> str:
    """Return a formatted message with an optional heading.

    The *heading* is normalized: trailing whitespace is stripped and any
    internal whitespace sequence is collapsed to a single space; leading
    whitespace is preserved.

    If both *heading* and *message* are non-empty (and not only contain
    whitespace), they are separated by a blank line. Blank lines within
    *message* are preserved.

    The *message* may span multiple lines. Each line is indented using
    *indentation* (a single space by default). Any trailing whitespace
    is removed from each line, while leading whitespace is preserved,
    which allows for custom indentation and spacing.

    An empty string is returned when both *heading* and *message* are
    empty or whitespace-only.
    """
    output: list[str] = []
    if heading and not heading.isspace():
        output.append(re.sub(r'(?<=\S)(\s+)(?=\S)', r' ', heading.rstrip()))
    if message and not message.isspace():
        output.append(indent(message, indentation))
    return '\n'.join(output)


def format_oserror(context: str, exc: OSError) -> str:
    """Stringify `OSError` exception *exc* using *context*.

    *context* is typically used to indicate what exactly was the caller
    doing when the exception was raised.
    """
    munged = munge_oserror(exc)

    # pylint: disable-next=unidiomatic-typecheck
    exc_label = 'OSError' if type(exc) is OSError else f'OS.{type(exc).__name__}'
    paths = f"'{munged['filename1']}'{f" ⟶ '{munged['filename2']}'" if munged['filename2'] else ''}"
    return f'{exc_label} [{munged['errcodes']}] {context} {paths}.\n{munged['strerror']}.'


def get_credentials(credentials_path: Path = Path.home() / '.credentials') -> dict[str, Any] | None:  # noqa: B008
    """Read credentials from *credentials_path*.

    If *credentials_path* is not provided a default path is used. To be
    precise, a `.credentials` file in the user's home directory.

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


def get_desktop_path() -> Path | None:
    """Get platform specific path for the desktop directory.

    If the directory could not be determined, `None` is returned.
    Even if the directory can be determined, it **may not** exist.
    """
    if sys.platform == 'win32':
        class GUID(Structure):  # pylint: disable=missing-class-docstring
            _fields_ = [('Data1', DWORD), ('Data2', WORD), ('Data3', WORD), ('Data4', BYTE * 8)]

        folder_id = GUID()
        windll.ole32.CLSIDFromString('{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}', byref(folder_id))
        path = LPWSTR()
        try:
            flags = 0
            access_token = None
            windll.shell32.SHGetKnownFolderPath(byref(folder_id), flags, access_token, byref(path))
            if path.value is not None:
                return Path(path.value)
        finally:
            windll.ole32.CoTaskMemFree(path)

    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        with contextlib.suppress(KeyError):
            return Path(environ['XDG_DESKTOP_DIR'])
        return Path.home() / 'Desktop'

    return None


def get_logger(name: str) -> Logger:
    """Get an instance of `legion.Logger` with the specified *name*.

    Unlike `logging.getLogger()`, the argument is **not** optional, so
    the root logger is **never** returned by default.

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


def munge_oserror(exc: OSError) -> dict[str, str | None]:
    """Process `OSError` exception *exc*.

    Process the `OSError` (or any of its subclasses) exception *exc* and
    return a dictionary with the attributes obtained from the instance.

    The keys and descriptions for the retrieved attributes are:
    - `errcodes: str`: the `errno` and `winerror` codes
    - `strerror: str`: the error message string, normalized (see below)
    - `filename1: str`: the first filename involved in the exception
    - `filename2: str`: the second filename involved in the exception

    Attributes are not guaranteed to exist, and in that case the stored
    value will be `None`, to make the dictionary easier to process, for
    examply for replacing missing values with a marker, etc.

    **NOTE**: the `errno` and `winerror` codes are combined with a slash
    character if both are present.

    **NOTE**: the returned error message is normalized if present. The
    first letter is uppercased and the final period (if any), removed.

    **NOTE**: depending on operation which caused the exception raising,
    there may be zero, one, or two paths involved.
    """
    exc_errno = None
    exc_winerror = None
    exc_errorcodes = None
    exc_message = None

    with contextlib.suppress(AttributeError):
        exc_winerror = f'WinError{exc.winerror}'

    with contextlib.suppress(KeyError):
        exc_errno = errorcode[exc.errno or -1]

    if exc_errno and exc_winerror:
        exc_errorcodes = f'{exc_errno}/{exc_winerror}'
    exc_errorcodes = exc_errorcodes or exc_errno or exc_winerror or None

    if exc.strerror:
        exc_message = f'{exc.strerror[0].upper()}{exc.strerror[1:].rstrip('.')}'

    return {
        'errcodes': exc_errorcodes,
        'strerror': exc_message,
        'filename1': fsdecode(exc.filename) if isinstance(exc.filename, bytes) else exc.filename,
        'filename2': fsdecode(exc.filename) if isinstance(exc.filename2, bytes) else exc.filename2,
    }


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


def timestamp(template: str = '%Y%m%d_%H%M%S') -> str:
    """Produce a timestamp string from current local date and time.

    The function is actually a simple alias for `strftime()`, but using
    a default common `template` for the formatting string. Actually, any
    valid `strftime()` compatible formatting string can be used.
    """
    return strftime(template)


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
        return windll.kernel32.GetConsoleMode(get_osfhandle(sys.stdout.fileno()), byref(c_uint()))   # pragma: no cover


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


    def wait_for_keypress(prompt: str = '\nPress any key to continue...') -> None:
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

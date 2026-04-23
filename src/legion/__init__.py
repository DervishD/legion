"""# legion {}

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
from collections.abc import Mapping
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

from .about import RELEASE

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from io import TextIOWrapper
    from types import TracebackType
    from typing import Any, LiteralString


__all__: list[str] = [  # pylint: disable=unused-variable
    'LegionLogger',
    'docs',
    'ensure_utf8_output',
    'excepthook',
    'format_message',
    'format_oserror',
    'generate_metadata_file',
    'get_credentials',
    'get_desktop_path',
    'get_logger',
    'git_repository_root',
    'load_pyproject',
    'munge_oserror',
    'resolve_version',
    'run',
    'timestamp',
    'wait_for_keypress',
]


if sys.platform == 'win32':
    from ctypes import byref, c_uint, create_unicode_buffer, Structure, windll
    from ctypes.wintypes import BYTE, DWORD, LPWSTR, MAX_PATH as _MAX_PATH_LEN, WORD
    from msvcrt import get_osfhandle, getch


class LegionLogger(logging.Logger):
    """Highly opinionated, extended logger.

    Drop-in replacement for `logging.Logger` with indentation support,
    multiline records and a simple but powerful configuration helper.

    It is intentionally opinionated about how logging should work, and
    although it provides a convenient configuration helper, it enforces
    a specific application-level logging model. For this reason, it is
    generally not suitable for reusable library modules. Its intended
    audience is applications, where authoritative logging configuration
    and consistent output are desirable.

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
    logger = legion.get_logger(__name__)

    # Then configure the logger with default or custom settings:
    logger.config()  # Check method documentation below for details.

    ```

    The following methods differ from or extend `logging.Logger`:
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

    return _unwrap_markdown(__doc__).format(RELEASE, visitor.get_full_docs())


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


# pylint: disable-next=too-many-locals
def _format_exception(exc: BaseException, chain_marker: str) -> str:
    """Format exception instance *exc* contents.

    Return a multiline string with the following items:
        - the exception type name, preceded by a *chain_marker* if it is
          the `__cause__` or the `__context__` of the previous exception
          and followed by a string representation of the exception.
        - the exception argument values, labelled.
        - the traceback.

    The string does **NOT** end in a newline character, every section is
    properly aligned and indented, and bullet-like markers are used for
    visual separation between items when needed. The actual format used
    is not relevant and no assumptions should be made about it.
    """
    exc_marker = '* '
    exc_indent = ' ' * len(exc_marker)
    tb_marker = '> '
    tb_indent = ' ' * len(tb_marker)
    exc_text = f'{exc}'.strip()

    formatted_exception = exc_marker
    formatted_exception += f'[{chain_marker}] ' if chain_marker else ''
    formatted_exception += type(exc).__name__
    formatted_exception += f': {exc_text}' if exc_text else ''
    formatted_exception += '\n'

    munged_exception_args = _munge_exception_args(exc)
    for label, value in munged_exception_args:
        formatted_exception += f'{exc_indent}{label}: {value}\n'
    formatted_exception += '\n' if munged_exception_args else ''

    current_frame_filename = None
    for filename, line, name, code in _munge_exception_traceback(exc):
        if current_frame_filename != filename:
            formatted_exception += f'{exc_indent}{tb_marker}{filename}:\n'
            current_frame_filename = filename
        formatted_exception += f'{exc_indent}{tb_indent}{line}, {name}{f': {code}' if code else ''}\n'
    return formatted_exception


def _munge_exception_args(exc: BaseException) -> list[tuple[str, str]]:
    """Process arguments from exception instance *exc*.

    Return a list with one item per processed argument. Can be empty if
    the exception instance does not have arguments. Each item is a tuple
    containing a label for the argument and its value, as strings.

    Labels are left-padded with spaces so they all have the same length.
    The labels are the canonical names of the argument types, except for
    `OSError` instances (and subclasses), where the labels are the names
    of the arguments rather than their types.

    Values are the printable representation of the argument objects, as
    returned by `repr()`.
    """
    if isinstance(exc, OSError):
        munged = munge_oserror(exc)
        labels = munged.keys()
        values = munged.values()
    else:
        labels = tuple(type(value).__name__ for value in exc.args)
        values = exc.args

    label_maxlen = max((len(label) for label in labels), default=0)

    munged_args: list[tuple[str, str]] = []
    for label, value in zip(labels, values, strict=True):
        munged_args.append((f'{label:>{label_maxlen}}', repr(value)))

    return munged_args


def _munge_exception_traceback(exc: BaseException) -> list[tuple[str, str, str, str]]:
    """Process traceback from exception instance *exc*.

    Return a list with one item per frame. Can be empty if no traceback
    is present in the exception instance.

    Each item is a tuple containing the frame filename, the line number,
    the function name (or equivalent) and the source code for the frame
    if available (or an empty string if not). All elements are strings,
    including the frame line number.
    """
    # """Extract traceback as a formatted string."""
    munged_traceback: list[tuple[str, str, str, str]] = []
    for frame in tb.extract_tb(exc.__traceback__):
        frame.lineno = frame.lineno or 1
        source_code = ''.join([
            line.strip() for line in linecache.getlines(frame.filename)[frame.lineno-1:frame.end_lineno]
        ])
        munged_traceback.append((frame.filename, str(frame.lineno), frame.name, source_code or frame.line or ''))
    return munged_traceback


def _get_exception_chain(exc: BaseException) -> list[tuple[BaseException, str]]:
    """Get an exception chain from *exc*.

    Return a list with one item per exception in *exc* chain. The chain
    is reversed, so the first element in the returned chain is the last
    exception in *exc* chain, the root cause for the chain. This is so
    the returned chain is expressed in *chronological* order, with the
    cause first, instead of the Python's default *structural* order with
    the effect, the last unhandled exception, appears first.
    """
    chain: list[tuple[BaseException, str]] = []
    seen: set[int] = set()
    cause___marker = ' __cause__ '  # Both markers must have same length.
    context_marker = '__context__'  # Both markers must have same length.

    while id(exc) not in seen:  # pragma: no branch
        seen.add(id(exc))  # Avoids technically 'impossible' cycles.

        if exc.__cause__ is not None:
            chain.append((exc, cause___marker))
            exc = exc.__cause__
        elif exc.__context__ is not None and not exc.__suppress_context__:
            chain.append((exc, context_marker))
            exc = exc.__context__
        else:
            chain.append((exc, ''))
            break

    chain.reverse()
    return chain


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

    chain = _get_exception_chain(exc_value)
    message = ''
    for exc, chain_marker in chain:
        message += _format_exception(exc, chain_marker) + '\n'

    logger = get_logger(__name__)
    logger.error(format_message(heading, message.rstrip()))


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
    paths = f"'{munged['filename1']}'{f" -> '{munged['filename2']}'" if munged['filename2'] else ''}"
    return f'{exc_label} [{munged['errcodes']}] {context} {paths}.\n{munged['strerror']}.'


def _deep_merge(defaults: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(defaults)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], Mapping) and isinstance(value, Mapping):
            result[key] = _deep_merge(result[key], cast('Mapping[str, Any]', value))
        else:
            result[key] = value
    return result


def generate_metadata_file(
    output_path_factory: Callable[[dict[str, Any]], Path | None],
    template: str,
    extra_metadata: dict[str, Any] | None = None,
) -> Path | None:
    """Generate a file by rendering a template using project metadata.

    The metadata is obtained from the `pyproject.toml` file contents, if
    available, and it is merged with *extra_metadata* if provided (it is
    `None` by default) so metadata keys can be appended or overridden if
    necessary, and an additional key named `project_root` containing the
    repository root is provided as as a default value which can be later
    overridden via `pyproject.toml` or *extra_metadata*. If the project
    version is absent from `pyproject.toml` or *extra_metadata*, it is
    resolved dynamically and injected into the combined metadata.

    The output file is generated using *output_path_factory*, which gets
    a copy of the retrieved metadata and returns the output `Path`. This
    allows the caller to produce an output file path using metadata:
    ```python
    template = '...'
    output_path_factory = lambda m: Path(m['project_root'] / 'src' / 'output.txt')
    generate_metadata_file(output_path_factory, template)
    ```
    If the factory returns `None`, no file is generated.

    The *template* is any `str.format_map()`-compatible template whose
    placeholders are filled from the merged metadata.

    The path of the written output file is returned, or `None` if any of
    the steps fails:
    - the project root cannot be determined.
    - the `pyproject.toml` file cannot be loaded (it is not found, it is
    not readable, it has syntax errors, etc.).
    - the project version cannot be resolved.
    - the *output_path_factory* returns `None`.

    **Note**: metadata dictionaries are deep-merged, so nested keys can
    be merged instead of entirely replaced, as would be the case with a
    shallow merge, which is the default for the `dict` union operator.
    """
    if (project_root := git_repository_root()) is None:
        return None

    if (package_metadata := load_pyproject(project_root)) is None:
        return None

    full_metadata = _deep_merge({'project_root': project_root} | package_metadata, extra_metadata or {})

    if 'version' not in full_metadata.get('project', {}):
        if (version := resolve_version()) is None:
            return None
        full_metadata['project']['version'] = version

    if (output_path := output_path_factory(full_metadata)) is not None:
        output_path.write_text(template.format_map(full_metadata), encoding='utf-8')

    return output_path


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


def get_logger(name: str) -> LegionLogger:
    """Get an instance of `legion.Logger` with the specified *name*.

    Unlike `logging.getLogger()`, the argument is **not** optional, so
    the root logger is **never** returned by default.

    This function temporarily registers `legion.Logger` as the default
    logger class, so the returned logger type is always guaranteed to be
    `legion.Logger`, no matter what other logger classes are registered.

    This is a convenience function to avoid having to register the class
    by hand, instantiate the logger, restore the previous class, etc.

    If a logger named *name* already exists in the logging registry, but
    under a different class, the function raises. This can happen if for
    some reason `logging.getLogger()` (or a different logger class) is
    used to create a logger with the same name before this function was
    called. The exception argument is the actual fully qualified type of
    the existing logger.
    """
    previous = logging.getLoggerClass()
    logging.setLoggerClass(LegionLogger)
    logger = None
    try:
        logger = logging.getLogger(name)
    finally:
        logging.setLoggerClass(previous)

    if not isinstance(logger, LegionLogger):
        wrong_type = f'{type(logger).__module__}.{type(logger).__name__}'
        raise TypeError(wrong_type)
    return logger


def git_repository_root(cwd: Path | None = None) -> Path | None:
    """Return the root directory of a Git repository.

    The lookup is performed relative to *cwd*. If not provided, then the
    current working directory is used.

    This function runs `git rev-parse --show-toplevel` and returns the
    fully resolved path of the repository root if the command succeeds,
    or `None` otherwise.
    """
    result = run(['git', 'rev-parse', '--show-toplevel'], cwd=(cwd or Path()).resolve(), encoding='utf-8')
    return None if result.returncode else Path(result.stdout.strip()).resolve()


def load_pyproject(project_dir: Path | None = None) -> dict[str, Any] | None:
    """Load `pyproject.toml` file and parse it into a dictionary.

    The file is assumed to be in `TOML` syntax.

    The file is looked up in *project_dir* if provided, otherwise in the
    root of the current Git repository. `None` is returned when the file
    does not exist or cannot be read, or if *project_dir* was not given
    and the root of the current Git repository cannot be determined.

    If the file can be found and its syntax is correct, a dictionary is
    returned, containing a representation of the file contents according
    to the `tomllib` parser. `TOMLDecodeError` is raised if the syntax
    of the `TOML` document is invalid.
    """
    if (pyproject_basedir := project_dir or git_repository_root()) is not None:
        pyproject_toml_path = pyproject_basedir.resolve() / 'pyproject.toml'
        with contextlib.suppress(PermissionError, FileNotFoundError):
            return tomllib.loads(pyproject_toml_path.read_text(encoding='utf-8'))
    return None


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
        'filename2': fsdecode(exc.filename2) if isinstance(exc.filename2, bytes) else exc.filename2,
    }


def resolve_version(template: str = '{tag}.post{distance}+{branch}{detached}.{rev}{dirty}') -> str | None:
    """Resolve the current version from VCS metadata.

    Return a version string generated from the repository VCS metadata,
    using the format string in *template*. If no metadata can be found,
    (e.g. the current working directory is not a repository, or it has
    no tags) then `None` is returned instead.

    A default value for *template* is used if it is not provided.

    The supported placeholders are:
    - `{tag}`: The most recent version tag, without a leading `v`.
    - `{distance}`: The number of commits since the tag.
    - `{branch}`: Current branch name, lowercased and sanitized, so it
    only contains characters in the `[a-z0-9]` set, replacing any other
    characters by `xxx`. It is an empty string if the repository is in
    the detached `HEAD` state.
    - `{detached}`: The string `detached` when the repository is in the
    detached `HEAD` state, otherwise it is an empty string.
    - `{rev}`: Abbreviated commit hash, without a leading `g`.
    - `{dirty}`: The string `.dirty` if the working tree has uncommitted
    changes, otherwise an empty string.

    All placeholders are optional, unused ones are silently ignored, but
    `KeyError` is raised if unknown placeholders are used in *template*.

    **NOTE**: with the default *template* the produced version string is
    fully compliant with the
    [`PyPA` version scheme](https://packaging.python.org/en/latest/specifications/version-specifiers/#version-scheme).
    All the supported placeholders produce fully compliant strings, too.
    To keep the resolved version string fully compliant, use only `+` as
    the local version specifier separator, and `.` as general separator.
    """
    branch_name_escape_sequence = 'xxx'
    dirty_marker = 'dirty'
    detached_head_marker = 'detached'

    if (result := run(['git', 'describe', '--long', f'--dirty=-{dirty_marker}'])).returncode:
        return None

    components = result.stdout.strip().split('-')

    dirty = f'.{dirty_marker}' if components[-1] == dirty_marker else ''
    tag, distance, rev = components[0:3]

    detached = ''
    branch = ''
    if not (result := run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])).returncode:
        branch = re.sub(r'[^a-z0-9]', branch_name_escape_sequence, result.stdout.strip().lower())
    else:
        detached = detached_head_marker

    placeholders = {
        'tag': tag.removeprefix('v'),
        'distance': distance,
        'branch': branch,
        'detached': detached,
        'rev': rev.removeprefix('g'),
        'dirty': dirty,
    }

    return template.format_map(placeholders)


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

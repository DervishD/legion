# legion

> 'What is your name?'\
> 'My name is Legion,' he replied, 'for we are many.'

Since this is many, it's *legion*. This package (currently, a single module) contains miscellaneous functions and constants used in some of the maintenance scripts of my private system. It is shared publicly in case the code may be useful to others.

## Constants
- `DESKTOP_PATH: pathlib.Path`\
    Path of user's desktop directory.
- `DEFAULT_CREDENTIALS_PATH: pathlib.Path`\
    Default filename used by `get_credentials()` for user credentials.
- `TIMESTAMP_FORMAT: str`\
    `time.strftime()` compatible format specification for timestamps.
- `ERROR_MARKER: str`\
    Marker string prepended to error messages.
- `ARROW_R: str`\
    Right-pointing arrow character for pretty-printing program output.
- `ARROW_L: str`\
    Left-pointing arrow character for pretty-printing program output.
- `UTF8: str`\
    Normalized name for `UTF-8` encoding.

## Classes
- `Logger`\
    Augmented functionality logger.

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
    - `makeRecord(`\
        `    *args: typing.Any,`\
        `    **kwargs: typing.Any`\
        `) -> logging.LogRecord`\
        Create a new logging record with indentation.

        Used internally by logger objects, can be called manually, too.
    - `set_indent(`\
        `    level: int`\
        `) -> None`\
        Set current logging indentation to *level*.

        *level* can be any positive integer or zero.

        For any other value, `ValueError` is raised.
    - `indent() -> None`\
        Increment current logging indentation level.
    - `dedent() -> None`\
        Decrement current logging indentation level.
    - `config(`\
        `    full_log_output: str | pathlib.Path | None = None,`\
        `    main_log_output: str | pathlib.Path | None = None,`\
        `    console: bool = True`\
        `) -> None`\
        Configure logger.

        This is an **authoritative, application-level setup call** that replaces any existing root logger configuration. It should be called **once and early** in the application lifecycle, before any other logging setup has been established.

        With the default configuration, the behavior of the logger is as follows:
        - **File logging**
            - *full_log_output*: receives *all* messages in detailed format (including a timestamp and some debugging info).
            - *main_log_output*: receives messages with severity `logging.INFO` or higher, with a simpler format but also timestamped.
            - If a file path is `None`, it is not created.
        - **Console logging** (if *console* is `True`):
            - No timestamps are included in the messages.
            - Messages with severity of exactly `logging.INFO` go to the standard output stream.
            - Messages with severity of `logging.WARNING` or higher go to the standard error stream.
        - If all file paths are `None` and *console* is `False`, **NO LOGGING OUTPUT IS PRODUCED AT ALL**.

## Functions
- `format_message(`\
    `    message: str = '',`\
    `    details: str = '',`\
    `    *,`\
    `    details_indent: str = ' '`\
    `) -> str`\
    Format *message*, including *details*. Both are optional.

    The *message* is sanitized: any trailing whitespace is stripped, and any sequence of internal whitespace is converted to a single space. Leading whitespace is preserved, though.

    If *details* are provided, they are appended to *message*. A newline character is used as a visual separator between them if *message* is not empty. The lines in *detail* are indented by *details_indent*, a a single space by default but any string can be used.

    Multiline *details* are supported and empty lines are preserved. For each line trailing whitespace is stripped and leading whitespace is preserved. This allows to use a per-line arbitrary indentation, and to have visual separation from *message* by including some newline characters at the very beginning of *details*.
- `excepthook(`\
    `    exc_type: type[BaseException],`\
    `    exc_value: BaseException,`\
    `    exc_traceback: types.TracebackType | None,`\
    `    *,`\
    `    heading: str = _DEFAULT_EXCEPTHOOK_HEADING`\
    `) -> None`\
    Log diagnostic information about unhandled exceptions.

    Intended for use as the default exception hook via `sys.excepthook`, either directly, via `functools.partial()`, or through an equivalent mechanism.

    Diagnostic information about the unhandled exception is logged using *exc_type*, *exc_value*, and *exc_traceback* arguments.

    The output is formatted as follows: the first line consists of the *heading* and the exception type name in parentheses. Any remaining diagnostic information is logged on subsequent lines as needed, and with a default indentation. If no *heading* is provided, a default string is used instead.

    Additional information is taken from the tuple of arguments passed to the exception constructor, with one entry per line including the type and the value for each argument.

    For `OSError` (and derived) exceptions these arguments are not very informative, so the specific attributes of this exception family are logged instead, one per line.

    Finally, a traceback is included if available.

    `KeyboardInterrupt` exceptions are not logged. Instead, the default exception hook is called to preserve keyboard interrupt behavior.
- `munge_oserror(`\
    `    exc: OSError`\
    `) -> tuple[str, str | None, str | None, str | None, str | None]`\
    Process `OSError` exception *exc*.

    Process the `OSError` (or any of its subclasses) exception *exc* and return a tuple with the attributes obtained from the instance.

    The types and descriptions of the retrieved attributes are:
    - `str`: the type name of *exc*
    - `str`: the `errno` and `winerror` codes
    - `str`: the error message string, normalized (see below)
    - `str`: the first filename involved in the exception
    - `str`: the second filename involved in the exception

    The only attribute guaranteed to always exist is the first one, the type name of *exc*, any other may not be present and then the stored value will be `None`, to make easier to process the tuple in order to replace missing values with a marker, etc.

    **NOTE**: the `errno` and `winerror` codes are combined with a slash character if both are present.

    **NOTE**: the returned error message is normalized if present. The first letter is uppercased and the final period (if any), removed.

    **NOTE**: depending on operation which caused the exception raising, there may be zero, one, or two paths involved.
- `format_oserror(`\
    `    context: str,`\
    `    exc: OSError`\
    `) -> str`\
    Stringify `OSError` exception *exc* using *context*.

    *context* is typically used to indicate what exactly was the caller doing when the exception was raised.
- `timestamp() -> str`\
    Produce a timestamp string from current local date and time.
- `run(`\
    `    command: collections.abc.Sequence[str],`\
    `    **kwargs: typing.Any`\
    `) -> subprocess.CompletedProcess[str]`\
    Run *command* with convenient defaults.

    Run *command*, using *kwargs* as arguments. Just a simple helper for `subprocess.run()` that provides convenient defaults.

    For that reason, the keyword arguments accepted in *kwargs* and the return value are the same ones used by `subprocess.run()` itself.
- `get_credentials(`\
    `    credentials_path: pathlib.Path = DEFAULT_CREDENTIALS_PATH`\
    `) -> dict[str, typing.Any] | None`\
    Read credentials from *credentials_path*.

    If *credentials_path* is not provided a default path is used. To be precise, the value of `DEFAULT_CREDENTIALS_PATH`.

    The credentials are returned as a simple dictionary. The dictionary has two levels: the first one groups credentials into sections, and the second contains the actual `key-value` pairs.

    Each credential is a `key-value` string pair, where the `key` is an identifier for the credential, and the `value` is the corresponding credential.

    If *credentials_path* cannot be read, or has syntax problems, `None` is returned. If it is empty, an empty dictionary is returned.
- `get_logger(`\
    `    name: str`\
    `) -> Logger`\
    Get an instance of `legion.Logger` with the specified *name*.

    Unlike `logging.getLogger()`, the argument is **not** optional, so the root logger is **never** returned.

    This function temporarily registers `legion.Logger` as the default logger class, so the returned logger type is always guaranteed to be `legion.Logger`, no matter what other logger classes are registered.

    This is a convenience function to avoid having to register the class by hand, instantiante the logger, restore the previous class, etc.
- `wait_for_keypress(`\
    `    prompt: str = _DEFAULT_WAIT_FOR_KEYPRESS_PROMPT`\
    `) -> None`\
    Wait for a keypress to continue in particular circumstances.

    If `sys.stdout` is attached to a transient console, the function prints a *prompt* message indicating that the program is paused until a key is pressed. If no *prompt* is provided as argument, a default string (in English) is used instead.

    It is a good idea to include a leading new line character in the *prompt* message to ensure it is clearly separated from previous output from the program.

    **NOTE**: there is no standard method of knowing if a console is transient or not, so determining console transience is entirely based on heuristics.

    **NOTE**: is up to the importer to register this function with `atexit.register()`, to call it explicitly, or to use it only if the importer is running as a script instead of being imported.
- `wait_for_keypress(`\
    `    *args: typing.Any,`\
    `    **kwargs: typing.Any`\
    `) -> None`\
    Stub for platforms where this function is not implemented.
- `docs() -> str`\
    Generate documentation for the module.

    Return a Markdown-formatted string containing the documentation for the module/package.

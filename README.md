# legion

> 'What is your name?'\
> 'My name is Legion,' he replied, 'for we are many.'

Since this is many, it's *legion*. This package (currently, a single module) contains miscellaneous functions and constants used in some of the maintenance scripts of my private system. It is shared publicly in case the code may be useful to others.

## Constants
- `ARROW_L: str`\
    Left-pointing arrow character for pretty-printing program output.
- `ARROW_R: str`\
    Right-pointing arrow character for pretty-printing program output.
- `DEFAULT_CREDENTIALS_PATH: pathlib.Path`\
    Default filename used by `get_credentials()` for user credentials.
- `DESKTOP_PATH: pathlib.Path`\
    Path of user's desktop directory.
- `ERROR_MARKER: str`\
    Marker string prepended to error messages.
- `PROGRAM_NAME: str`\
    User-friendly name of the currently executing script.
- `PROGRAM_PATH: pathlib.Path`\
    Path of the currently executing script.
- `TIMESTAMP_FORMAT: str`\
    `time.strftime()` compatible format specification for timestamps.
- `UTF8: str`\
    Normalized name for `UTF-8` encoding.
- `logger`\
    Default per-application logger instance.

    Its interface is identical to `logging.Logger` objects but it also includes indentation support and a simple configuration function:
    - `logger.config(`\
        `    full_log_output: str | Path | None,`\
        `    main_log_output: str | Path | None,`\
        `    console: bool`\
        `) -> None`\
        Configure logger.

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
    - `logger.dedent() -> None`\
        Decrement current logging indentation level.
    - `logger.indent() -> None`\
        Increment current logging indentation level.
    - `logger.makeRecord(`\
        `    args: Any,`\
        `    kwargs: Any`\
        `) -> logging.LogRecord`\
        Create a new logging record with indentation.

        Used internally by logger objects, can be called manually, too.
    - `logger.set_indent(`\
        `    level: int`\
        `) -> None`\
        Set current logging indentation to *level*.

        *level* can be any positive integer or zero.

        For any other value, `ValueError` is raised.

## Functions
- `demo() -> None`\
    Demonstrate package features.
- `docs() -> str`\
    Generate documentation for the module.

    Return a Markdown-formatted string containing the documentation for the module/package.
- `excepthook(`\
    `    exc_type: type[BaseException],`\
    `    exc_value: BaseException,`\
    `    exc_traceback: TracebackType | None,`\
    `    *,`\
    `    unhandled_exception_banner: str,`\
    `    unhandled_oserror_banner: str,`\
    `    error_dialog_title: str`\
    `) -> None`\
    Log unhandled exceptions.

    Intended to be used as default exception hook in `sys.excepthook`.

    Unhandled exceptions are logged, using the provided arguments, that is, the exception type (*exc_type*), its value (*exc_value*) and the associated traceback (*exc_traceback*).

    The formatting can be customized by using the following keyword-only arguments, but if not provided, default strings are used:
    - *unhandled_exception_banner*
    - *unhandled_oserror_banner*
    - *error_dialog_title*

    **NOTE**: in order to provide this formatting arguments when using the function as `sys.excepthook`, `functools.partial()` can be used to create a new function with the desired defaults, but other alternative mechanisms can be used as well.

    A banner is prepended to the exception information, depending on the type of the exception: for `OSError` exception, the banner used is *unhandled_oserror_banner* and for the rest of possible exceptions, *unhandled_exception_banner* is used.

    For `OSError` exceptions, any additional information included in the exception object is gathered and shown, and no traceback is logged.

    For any other exception, arguments contained in the exception object are included, if present, together with the traceback if available.

    `KeyboardInterrupt` exceptions are not logged. Instead, the default exception hook is called to preserve keyboard interrupt behavior.

    Finally, depending on the platform, a modal dialog may be shown to ensure the end user notices the error, titled *error_dialog_title*.
- `format_error(`\
    `    message: str,`\
    `    details: str,`\
    `    *,`\
    `    banner: str,`\
    `    details_header: str,`\
    `    details_line_prefix: str,`\
    `    details_footer: str`\
    `) -> str`\
    Format error *message* and, optionally, *details*.

    First, `ERROR_MARKER` and *banner* are prepended to *message*. All the subsequent lines are indented so they are visually aligned under the end of the `ERROR_MARKER`.

    If *details* are provided, they are appended to *message*, separated by a new line character and *details_header*. Each line in *details* is prepended by *details_line_prefix*. Finally, *details_footer* is appended, ending the details section.

    Leading and internal spaces, as well as blank lines, are preserved in both *message* and *details*, but trailing spaces are removed.

    The formatting can be customized using the following keyword-only arguments, but if not provided, default strings are used instead:
    - *banner*
    - *details_header*
    - *details_line_prefix*
    - *details_footer*

    Usually, the customization can be done using `functools.partial()` to create a new function with the desired defaults, so that they do not have to be provided every time the function is called.
- `format_oserror(`\
    `    context: str,`\
    `    exc: OSError`\
    `) -> str`\
    Stringify `OSError` exception *exc* using *context*.

    *context* is typically used to indicate what exactly was the caller doing when the exception was raised.
- `get_credentials(`\
    `    credentials_path: Path`\
    `) -> dict[str, Any] | None`\
    Read credentials from *credentials_path*.

    If *credentials_path* is not provided a default path is used. To be precise, the value of `DEFAULT_CREDENTIALS_PATH`.

    The credentials are returned as a simple dictionary. The dictionary has two levels: the first one groups credentials into sections, and the second contains the actual `key-value` pairs.

    Each credential is a `key-value` string pair, where the `key` is an identifier for the credential, and the `value` is the corresponding credential.

    If *credentials_path* cannot be read, or has syntax problems, `None` is returned. If it is empty, an empty dictionary is returned.
- `munge_oserror(`\
    `    exc: OSError`\
    `) -> tuple[str, str, str, str, str]`\
    Process `OSError` exception *exc*.

    Process the `OSError` (or any of its subclasses) exception *exc* and return a tuple containing the processed information.

    First item is the actual `OSError` subclass that was raised, as a string.

    Second item are the `errno` and `winerror` numeric codes. They are combined with a slash character if both are present. If no numeric codes exist in *exc*, a marker is used instead.

    The third item is the error message. The first letter is uppercased and a final period is added. If it does not exist, an empty string is used instead.

    The final two items are the paths involved in the *exc* exception, if any, as strings. Depending on the actual exception, there may be zero, one, or two paths involved. If some of the paths do not exist in *exc*, they will be anyway returned in the tuple as `None`.
- `run(`\
    `    command: Sequence[str],`\
    `    kwargs: Any`\
    `) -> subprocess.CompletedProcess[str]`\
    Run *command* with convenient defaults.

    Run *command*, using *kwargs* as arguments. Just a simple helper for `subprocess.run()` that provides convenient defaults.

    For that reason, the keyword arguments accepted in *kwargs* and the return value are the same ones used by `subprocess.run()` itself.
- `timestamp() -> str`\
    Produce a timestamp string from current local date and time.
- `wait_for_keypress(`\
    `    prompt: str`\
    `) -> None`\
    Wait for a keypress to continue in particular circumstances.

    If `sys.stdout` is attached to a transient console, the function prints a *prompt* message indicating that the program is paused until a key is pressed. If no *prompt* is provided as argument, a default string (in English) is used instead.

    It is a good idea to include a leading new line character in the *prompt* message to ensure it is clearly separated from previous output from the program.

    **NOTE**: there is no standard method of knowing if a console is transient or not, so determining console transience is entirely based on heuristics.

    **NOTE**: is up to the importer to register this function with `atexit.register()`, to call it explicitly, or to use it only if the importer is running as a script instead of being imported.

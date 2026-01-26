# legion

`legion` Python module contains miscellaneous functions and constants for the
maintenance scripts of my private system. It is shared in this public repository
just in case its code may be of help for other programmers.

The current API (symbols and functions) follows.

## Symbols
- Module constants:
    - `DESKTOP_PATH`<br>
        Path of user's desktop directory.
    - `PROGRAM_PATH`<br>
        Path of the currently executing script.
    - `PROGRAM_NAME`<br>
        User friendly name of the currently executing script.
    - `LEGION_VERSION`<br>
        Currently installed version of this module.
    - `DEFAULT_CREDENTIALS_PATH`<br>
        Filename used by default by `get_credentials()` for user credentials.
    - `TIMESTAMP_FORMAT`<br>
        `time.strftime()` compatible format specification for timestamps.
    - `ERROR_MARKER`<br>
        Marker string prepended to error messages.
    - `ARROW_R`<br>
        Right pointing arrow character for pretty-printing program output.
    - `ARROW_L`<br>
        Left pointing arrow character for pretty-printing program output.
    - `UTF8`<br>
        Normalized name for `UTF-8` encoding.
- `WFKStatuses`<br>
    Available for `win32`platform, only, they are the possible return values for
    `wait_for_keypress()`, implemented for now as an `IntEnum`:
    - `WFKStatuses.NO_WIN32`<br>
        Do not wait for keypress, no `win32` platform.
    - `WFKStatuses.NO_CONSOLE_ATTACHED`<br>
        Do not wait for keypress, no console attached.
    - `WFKStatuses.NO_CONSOLE_TITLE`<br>
        Do not wait for keypress, no console title.
    - `WFKStatuses.NO_TRANSIENT_FROZEN`<br>
        Do not wait for keypress, no transient console with frozen executable.
    - `WFKStatuses.NO_TRANSIENT_PYTHON`<br>
        Do not wait for keypress, no transient console with `Python` script.
    - `WFKStatuses.WAIT_FOR_KEYPRESS`<br>
        Wait for keypress.
- `logger`<br>
    Default per-application logger instance. Its public interface is identical
    to `logging.Logger` objects but it also includes indentation support and a
    simple configuration system by adding the following methods:
    - `set_indent(level: int) -> None`<br>
    Set current logging indentation to *level*.<br>
    *level* can be any positive integer or zero.<br>
    For any other value, `ValueError` is raised.
    - `indent() -> None`
    Increment current logger indentation level.
    - `dedent() -> None`
    Decrement current logger indentation level.
    - `config(`<br>
        `    full_log_output: str|Path|None = None,`<br>
        `    main_log_output: str|Path|None = None,`<br>
        `    console: bool = True`<br>
        `) -> None`<br>
    Configure logger.<br>
    With the default configuration **ALL** logging messages are sent to
    *full_log_output* using a detailed format which includes the current
    timestamp and some debugging information; messages with severity of
    `logging.INFO` or higher, intended to be the typical program output, are
    sent to *main_log_output*, also timestamped.<br>
    In addition to that, and if console is `True` (the default), the messages
    with a severity of `logging.INFO` (and only those) are sent to the standard
    output stream, and messages with a severity of `logging.WARNING` or higher
    are sent to the standard error stream, without a timestamp in both
    cases.<br>
    If *full_log_output* or *main_log_output* are `None` (they are, by default),
    then the corresponding files are not created and no logging message will go
    there. In this case, if *console* is set to `False`, **NO LOGGING OUTPUT
    WILL BE PRODUCED AT ALL**.

## Functions
- `error(`<br>
  `    message: str,`<br>
  `    details: str = ''`<br>
  `) -> None`<br>
    Preprocess and log *message*, optionally including *details*.<br>
    Both an error marker and a header are prepended to *message*, and a visual
    separator is prepended to *details*. In addition to this both *message* and
    *details* are indented.<br>
    Finally, everything is logged using `logger.error()`.
- `excepthook(`<br>
  `    exc_type: type[BaseException],`<br>
  `    exc_value: BaseException,`<br>
  `    exc_traceback: TracebackType | None`<br>
  `) -> None`<br>
    Log unhandled exceptions.<br>
    Unhandled exceptions are logged, using the provided arguments, that is, the
    exception type (*exc_type*), its value (*exc_value*) and the associated
    traceback (*exc_traceback*).<br>
    For `OSError` exceptions a different format is used, which includes any
    additional `OSError` information, and no traceback is logged.<br>
    For any other exception, a generic message is logged together with the
    traceback, if available.<br>
    `KeyboardInterrupt` exceptions are not logged, the default exception hook is
    called instead to have normal keyboard interrupt behavior.<br>
    Finally, depending on the platform, some kind of modal dialog shows so the
    end user does not miss the error.<br>
    Intended to be used as default exception hook (`sys.excepthook`).
- `munge_oserror(`<br>
  `    exception: OSError`<br>
  `) -> tuple[str, str, str, str, str]`<br>
    Process `OSError` exception objects.<br>
    Process the *exception* object for an `OSError` exceptions (or any
    subclass), and return a tuple containing the processed information.<br>
    First item is the actual `OSError` subclass which was raised, as a
    string.<br>
    Second item are the `errno` and `winerror` numeric codes. They are combined
    with a slash character if both are present. If no numeric codes exist in the
    exception object, a marker is used instead.<br>
    The third item is the error message. The first letter is uppercased and a
    final period is added. If it does not exist, an empty string is used
    instead.<br>
    The final two items are the paths involved in the exception, if any, as
    strings. Depending on the actual exception there may be zero, one or two
    paths involved. If some of the paths are not present in the exception
    object, it will anyway exist in the returned tuple but its value will be
    `None`.
- `format_oserror(`<br>
  `    context: str,`<br>
  `    exc: OSError`<br>
  `) -> None`<br>
    Generate a string from `OSError` *exc* and *context*.
- `timestamp() -> str`<br>
    Produce a timestamp string from current local date and time.
- `run(`<br>
  `    command: Sequence[str],`<br>
  `    **: Any`<br>
  `) -> subprocess.CompletedProcess[str]`<br>
    Run a command.<br>
    Run *command*, using *args* as arguments. This is just a very simple helper
    for the `subprocess.run()` function to make such calls easier and more
    convenient by providing some defaults for the arguments.<br>
    For that reason, the keyword arguments accepted in *args* and the return
    value are the same ones used by `subprocess.run()` itself.
- `wait_for_keypress() -> WFKStatuses`<br>
    Wait for a keypress to continue in particular circumstances.<br>
    If `sys.stdout` has an actual console attached **AND** it is a transient
    console, this function will print a simple message for the end user telling
    that the program is paused until any key is pressed.<br>
    For `win32` platform only.
- `get_credentials(`<br>
  `    credentials_path: Path = DEFAULT_CREDENTIALS_PATH`<br>
  `) -> dict[str, Any] | None`<br>
    Read credentials from *credentials_path*.<br>
    If *credentials_path* if not provided as argument, a default path is used
    instead (the value of `DEFAULT_CREDENTIALS_PATH`).<br>
    The credentials are returned as a simple two-level dictionary, with the
    first level consisting in different sections, intended to group credentials,
    and the second level being the credentials themselves.<br>
    Each credential is a `key-value` string pair, where the `key` is an
    identifier for the credential, and the `value` is the corresponding
    credential.<br>
    If *credentials_path* cannot be read or has syntax problems, `None` is
    returned instead.

## API notes and side effects
- Both `sys.stdout` and `sys.stderr` are automatically reconfigured into UTF-8
  mode.
- Very basic logging configuration is performed even when `logger.setup()` is
  not called: all logging messages will be handled and sent to console with a
  default format (currently, just the logging message, without any context), and
  all default logging handlers are removed from the root logger after closing
  them. No indentation of logging messages is possible.
- A new logging class is set up by the logger, with indentation support, so
  **ALL** new loggers created by the application importing this module will have
  that new class (not exposed on purpose). This can be changed at any time by
  the application by calling `logging.setLoggerClass()` with the desired class.
- The provided exception hook is registered at `sys.excepthook`. The previously
  registered one is still accessible at `sys.__excepthook__` if needed.
- Under `win32`, an `atexit` handler is registered which waits for a keypress
  when the program exits if it is running on a transient console.
- If the module is run rather than imported, it prints some demos. Currently, a
  timestamp and the names and values of all constants which are valid in all
  platforms.

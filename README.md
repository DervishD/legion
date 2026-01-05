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
    - `DEFAULT_CREDENTIALS_FILE`<br>
        Filename used by default by `get_credentials()` for user credentials.
    - `TIMESTAMP_FORMAT`<br>
        `time.strftime()` compatible format specification for timestamps.
    - `ARROW_L`<br>
        Left pointing arrow character for pretty-printing program output.
    - `ARROW_R`<br>
        Right pointing arrow character for pretty-printing program output.
    - `ERROR_MARKER`<br>
        Marker string prepended to error messages.
    - `UTF8`<br>
        Normalized name for `UTF-8` encoding.
- `WFKStatuses`<br>
    Available for `win32`platform, only, they are the possible return values for `wait_for_keypress()`, implemented for now as an `IntEnum`:
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
    Set the logger indentation level to `level`. Negative values are ignored
    and zero is used instead.
    - `indent() -> None`
    Increment current logger indentation level.
    - `dedent() -> None`
    Decrement current logger indentation level.
    - `config(`<br>
        `    debugfile: str|Path|None = None,`<br>
        `    logfile: str|Path|None = None,`<br>
        `    console: bool = True`<br>
        `) -> None`<br>
    Configure logger.

    With the default configuration **ALL** logging messages are sent to
    `debugfile` with a timestamp and some debugging information; those messages
    with severity of `logging.INFO` or higher are sent to `logfile`, also
    timestamped.

    In addition to that, and if `console` is `True` (the default), messages with
    a severity of `logging.INFO` (and only those) are sent to the standard
    output stream, and messages with a severity of `logging.WARNING` or higher
    are sent to the standard error stream, without a timestamp in both cases.

    If `debugfile` or `logfile` are `None` (the default), then the corresponding
    files are not created and no logging message will go there. In this case, if
    `console` is `False`, **NO LOGGING OUTPUT WILL BE PRODUCED AT ALL**.


## Functions
- `error(`<br>
  `    message: str,`<br>
  `    details: str = ''`<br>
  `) -> None`<br>
    Preprocess and log error `message`, optionally including `details`.

    A header/marker is prepended to the `message`, and a visual separator is
    prepended to the `details`. Both the `message` and the `details` are
    indented.

    Finally, everything is logged using `logging.error()`.
- `excepthook(`<br>
  `    exc_type: type[BaseException],`<br>
  `    exc_value: BaseException,`<br>
  `    exc_traceback: TracebackType | None`<br>
  `) -> None`<br>
    Log information about unhandled exceptions using the provided exception
    `type`, `value` and associated `traceback`.

    For `KeyboardInterrupt` exceptions, no logging is performed, the default
    exception hook is used instead.

    For `OSError` exceptions, a different message is logged, including
    particular `OSError` information, and no `traceback` is logged.

    For any other unhandled exception, a generic message is logged together with
    the `traceback`, if available.

    Finally, depending on the platform, some kind of modal dialog is shown so
    the end user does not miss the error.

    Intended to be used as default exception hook (`sys.excepthook`).
- `munge_oserror(`<br>
  `    exception: OSError`<br>
  `) -> tuple[str, str, str, str, str]`<br>
    Process the `exception` object for `OSError` exceptions (and its
    subclasses), and return a tuple containing the processed information.

    First item is the actual `OSError` subclass which was raised, as a string.

    Second item is the `errno` and `winerror` codes, separated by a slash if
    both are present. If no error codes exist in the `exception` object, this
    item is replaced by an informative placeholder.

    The third item is the error message, starting with an uppercase letter and
    ending in a period. If it does not exist, it will be an empty string.

    Final two items are the filenames involved in the `exception`. Depending on
    the actual `exception`, there may be zero, one or two filenames involved. If
    some of the filenames is not present in the `exception` object, it will
    still be in the tuple but it's value will be `None`.
- `prettyprint_oserror(`<br>
  `    reason: str,`<br>
  `    exc: OSError`<br>
  `) -> None`<br>
    Print a very simple `OSError` message using the `reason` and `exception`
    information.
- `timestamp() -> str`<br>
    Produce a timestamp string from current local date and time.
- `run(`<br>
  `    command: Sequence[str],`<br>
  `    **subprocess_args: Any`<br>
  `) -> subprocess.CompletedProcess[str]`<br>
    Run `command`, using `subprocess_args` as arguments. This is just a helper
    for `subprocess.run()` to make such calls more convenient by providing a set
    of defaults for the arguments.

    For that reason, the keyword arguments accepted in `subprocess_args` and the
    return value for this function are the exact same ones accepted and returned
    by the `subprocess.run()` function itself.
- `wait_for_keypress() -> WFKStatuses`<br>
    Wait for a keypress to continue if `sys.stdout` is a real console **AND**
    the console is transient.

    For `win32` platform only.
- `get_credentials(`<br>
  `    credentials_path: Path = _Config.CREDENTIALS_FILE`<br>
  `) -> dict[str, Any] | None`<br>
    Get credentials for current user, from the file at `credentials_path`.

    If `credentials_path` if not provided as argument, a default path is used.

    No matter the actual syntax of the file, which may change in the future, the
    credentials are returned as a simple two-levels dictionary. The first level
    are the different sections, intended to group credentials. The second level
    are the credentials themselves. They are accessed by credential identifier
    and returned as strings.

    If credentials file cannot be read or has syntax problems, `None` is
    returned.

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

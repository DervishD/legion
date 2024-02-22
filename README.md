<!-- cspell: ignore atexit munge oserror -->
# legion

`legion` Python module contains miscellaneous functions and constants for the
maintenance scripts of my private system. It is shared in this public repository
just in case its code may be of help for other programmers.

The current API (constants and functions) follows.

## Constants
- `DESKTOP_PATH`<br>
    Path of user's Desktop directory.
- `PROGRAM_PATH`<br>
    Path of the currently executing script.
- `PROGRAM_NAME`<br>
    User friendly name of the currently executing script.
- `ARROW_L`<br>
    Left pointing arrow character for pretty-printing program output.
- `ARROW_R`<br>
    Right pointing arrow character for pretty-printing program output.
- `UTF8`<br>
    Normalized name for UTF-8 encoding.
- `WFKStatuses(IntEnum)` Return values for `wait_for_keypress()`, `win32`only:
    - `NO_WIN32`<br>
        Do not wait for keypress, no `win32` platform.
    - `NO_CONSOLE_ATTACHED`<br>
        Do not wait for keypress, no console attached.
    - `NO_CONSOLE_TITLE`<br>
        Do not wait for keypress, no console title.
    - `NO_TRANSIENT_FROZEN`<br>
        Do not wait for keypress, no transient console with frozen executable.
    - `NO_TRANSIENT_PYTHON`<br>
        Do not wait for keypress, no transient console with Python script.
    - `WAIT_FOR_KEYPRESS`<br>
        Wait for keypress.

## Functions
- `error(message, details='')`
- `excepthook(type, value, traceback)`
- `munge_oserror(exception)`
- `prettyprint_oserror(exception)`
- `timestamp()`
- `run(*command, **subprocess_args)`
- `setup_logging(debugfile=None, logfile=None, console=True)`
- `logging.indent(level=None)`
- `logging.dedent(level=None)`
- `wait_for_keypress()` `win32` only.
- `get_credentials()`

## API notes and side effects
- Both `sys.stdout` and `sys.stderr` are automatically reconfigured into UTF-8
  mode.
- Very basic logging configuration is performed even when `setup_logging()` is
  not called: all logging messages will be handled and sent to console with a
  default format (currently, just the logging message, without any context), and
  all default logging handlers are removed from the root logger after closing
  them. No indentation of logging messages is possible.
- The provided exception hook is registered at `sys.excepthook`. The previously
  registered one is still accessible at `sys.__excepthook__` if needed.
- Under `win32`, an `atexit` handler is registered which waits for a keypress
  when the program exits if it is running on a transient console.
- If the module is run rather than imported, it prints some demos. Currently, a
  timestamp and the names and values of all constants which are valid in all
  platforms.

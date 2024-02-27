<!-- cspell: ignore atexit errno munge oserror -->
# legion

`legion` Python module contains miscellaneous functions and constants for the
maintenance scripts of my private system. It is shared in this public repository
just in case its code may be of help for other programmers.

The current API (constants and functions) follows.

## Constants
- `DESKTOP_PATH`<br>
    Path of user's `Desktop` directory.
- `PROGRAM_PATH`<br>
    Path of the currently executing script.
- `PROGRAM_NAME`<br>
    User friendly name of the currently executing script.
- `ARROW_L`<br>
    Left pointing arrow character for pretty-printing program output.
- `ARROW_R`<br>
    Right pointing arrow character for pretty-printing program output.
- `UTF8`<br>
    Normalized name for `UTF-8` encoding.
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
        Do not wait for keypress, no transient console with `Python` script.
    - `WAIT_FOR_KEYPRESS`<br>
        Wait for keypress.

## Functions
- `error(message, details='')`<br>
    Preprocess and log error `message`, optionally including `details`.

    A header/marker is prepended to the `message`, and a visual separator is
    prepended to the `details`. Both the `message` and the `details` are
    indented.

    Finally, everything is logged using `logging.error()`.
- `excepthook(type, value, traceback)`<br>
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
- `munge_oserror(exception)`<br>
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
- `prettyprint_oserror(reason, exception)`<br>
    Print a very simple `OSError` message using the `reason` and `exception`
    information.
- `timestamp()`<br>
    Produce a timestamp string from current local date and time.
- `run(*command, **subprocess_args)`<br>
    Run `command`, using `subprocess_args` as arguments. This is just a helper
    for `subprocess.run()` to make such calls more convenient by providing a set
    of defaults for the arguments.

    For that reason, the keyword arguments accepted in `subprocess_args` and the
    return value for this function are the exact same ones accepted and returned
    by the `subprocess.run()` function itself.
- `setup_logging(debugfile=None, logfile=None, console=True)`<br>
    Set up logging system, disabling all existing loggers.

    With the current configuration ALL logging messages are sent to `debugfile`
    and `logging.INFO` messages are sent to `logfile`, timestamped.

    In addition to that, and if `console` is `True` (the default), all
    `logging.INFO` messages are sent to the console too, but without a
    timestamp.

    If `debugfile` or `logfile` are `None`, the corresponding files are not
    created and no logging message will go there. In this case, if console is
    `False`, **NO LOGGING OUTPUT WILL BE PRODUCED AT ALL**.
- `logging.indent(level=None)`<br>
    If `level` is provided, set the current logging indentation level to that
    number, meaning that logging messages will be prepended with that many
    copies of the current logging indentation character.

    If `level` is not provided or is `None`, the current logging indentation
    level is *increased* in 1 copy of the current logging indentation character.
- `logging.dedent(level=None)`<br>
    If `level` is provided, set the current logging indentation level to that
    number, meaning that logging messages will be prepended with that many
    copies of the current logging indentation character.

    If `level` is not provided or is `None`, the current logging indentation
    level is *decreased* in 1 copy of the current logging indentation character.
- `wait_for_keypress()`<br>
    Wait for a keypress to continue if `sys.stdout` is a real console **AND**
    the console is transient.

    For `win32` platform only.
- `get_credentials(credentials_path=<default credentials path>)`<br>
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

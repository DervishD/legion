# legion 2.1.0

> 'What is your name?'\
> 'My name is Legion,' he replied, 'for we are many.'

Since this is many, it's *legion*. This package (currently, a single module) contains miscellaneous functions and constants used in some of the maintenance scripts of my private system. It is shared publicly in case the code may be useful to others.

## API reference
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
- `docs() -> str`\
    Return this module documentation in Markdown format.
- `ensure_utf8_output(`\
    `    f: collections.abc.Callable[P, R]`\
    `) -> collections.abc.Callable[P, R]`\
    Ensure UTF-8 encoding on output streams for the wrapped function.

    Reconfigure standard output streams so they use UTF-8 encoding even if they are redirected to a file when running the program from the command line, particularly on win32 platform, where the encoding in that case is locale-dependent and may not be UTF-8.
- `excepthook(`\
    `    exc_type: type[BaseException],`\
    `    exc_value: BaseException,`\
    `    exc_traceback: types.TracebackType | None,`\
    `    *,`\
    `    heading: str = 'Unhandled exception'`\
    `) -> None`\
    Log diagnostic information about unhandled exceptions.

    Intended for use as the default exception hook via `sys.excepthook`, either directly, via `functools.partial()`, or through an equivalent mechanism.

    Diagnostic information about the unhandled exception is logged using *exc_type*, *exc_value*, and *exc_traceback* arguments.

    The output is formatted as follows: the first line consists of the *heading* and the exception type name in parentheses. Any remaining diagnostic information is logged on subsequent lines as needed, and with a default indentation. If no *heading* is provided, a default string is used instead.

    Additional information is taken from the tuple of arguments passed to the exception constructor, with one entry per line including the type and the value for each argument.

    For `OSError` (and derived) exceptions these arguments are not very informative, so the specific attributes of this exception family are logged instead, one per line.

    Finally, a traceback is included if available.

    `KeyboardInterrupt` exceptions are not logged. Instead, the default exception hook is called to preserve keyboard interrupt behavior.
- `format_message(`\
    `    heading: str,`\
    `    message: str,`\
    `    *,`\
    `    indentation: str = ' '`\
    `) -> str`\
    Return a formatted message with an optional heading.

    The *heading* is normalized: trailing whitespace is stripped and any internal whitespace sequence is collapsed to a single space; leading whitespace is preserved.

    If both *heading* and *message* are non-empty (and not only contain whitespace), they are separated by a blank line. Blank lines within *message* are preserved.

    The *message* may span multiple lines. Each line is indented using *indentation* (a single space by default). Any trailing whitespace is removed from each line, while leading whitespace is preserved, which allows for custom indentation and spacing.

    An empty string is returned when both *heading* and *message* are empty or whitespace-only.
- `format_oserror(`\
    `    context: str,`\
    `    exc: OSError`\
    `) -> str`\
    Stringify `OSError` exception *exc* using *context*.

    *context* is typically used to indicate what exactly was the caller doing when the exception was raised.
- `generate_metadata_file(`\
    `    output_path_factory: collections.abc.Callable[[dict[str, typing.Any]], pathlib.Path | None],`\
    `    template: str,`\
    `    extra_metadata: dict[str, typing.Any] | None = None`\
    `) -> pathlib.Path | None`\
    Generate a file by rendering a template using project metadata.

    The metadata is obtained from the `pyproject.toml` file contents, if available, and it is merged with *extra_metadata* if provided (it is `None` by default) so metadata keys can be appended or overridden if necessary, and an additional key named `project_root` containing the repository root is provided as as a default value which can be later overridden via `pyproject.toml` or *extra_metadata*. If the project version is absent from `pyproject.toml` or *extra_metadata*, it is resolved dynamically and injected into the combined metadata.

    The output file is generated using *output_path_factory*, which gets a copy of the retrieved metadata and returns the output `Path`. This allows the caller to produce an output file path using metadata: ```python template = '...' output_path_factory = lambda m: Path(m['project_root'] / 'src' / 'output.txt') generate_metadata_file(output_path_factory, template) ``` If the factory returns `None`, no file is generated.

    The *template* is any `str.format_map()`-compatible template whose placeholders are filled from the merged metadata.

    The path of the written output file is returned, or `None` if any of the steps fails:
    - the project root cannot be determined.
    - the `pyproject.toml` file cannot be loaded (it is not found, it is not readable, it has syntax errors, etc.).
    - the project version cannot be resolved.
    - the *output_path_factory* returns `None`.

    **Note**: metadata dictionaries are deep-merged, so nested keys can be merged instead of entirely replaced, as would be the case with a shallow merge, which is the default for the `dict` union operator.
- `get_credentials(`\
    `    credentials_path: pathlib.Path = pathlib.Path.home() / '.credentials'`\
    `) -> dict[str, typing.Any] | None`\
    Read credentials from *credentials_path*.

    If *credentials_path* is not provided a default path is used. To be precise, a `.credentials` file in the user's home directory.

    The credentials are returned as a simple dictionary. The dictionary has two levels: the first one groups credentials into sections, and the second contains the actual `key-value` pairs.

    Each credential is a `key-value` string pair, where the `key` is an identifier for the credential, and the `value` is the corresponding credential.

    If *credentials_path* cannot be read, or has syntax problems, `None` is returned. If it is empty, an empty dictionary is returned.
- `get_desktop_path() -> pathlib.Path | None`\
    Get platform specific path for the desktop directory.

    If the directory could not be determined, `None` is returned. Even if the directory can be determined, it **may not** exist.
- `get_logger(`\
    `    name: str`\
    `) -> Logger`\
    Get an instance of `legion.Logger` with the specified *name*.

    Unlike `logging.getLogger()`, the argument is **not** optional, so the root logger is **never** returned by default.

    This function temporarily registers `legion.Logger` as the default logger class, so the returned logger type is always guaranteed to be `legion.Logger`, no matter what other logger classes are registered.

    This is a convenience function to avoid having to register the class by hand, instantiante the logger, restore the previous class, etc.
- `git_repository_root(`\
    `    cwd: pathlib.Path | None = None`\
    `) -> pathlib.Path | None`\
    Return the root directory of a Git repository.

    The lookup is performed relative to *cwd*. If not provided, then the current working directory is used.

    This function runs `git rev-parse --show-toplevel` and returns the fully resolved path of the repository root if the command succeeds, or `None` otherwise.
- `load_pyproject(`\
    `    project_dir: pathlib.Path | None = None`\
    `) -> dict[str, typing.Any] | None`\
    Load `pyproject.toml` file and parse it into a dictionary.

    The file is assumed to be in `TOML` syntax.

    The file is looked up in *project_dir* if provided, otherwise in the root of the current Git repository. `None` is returned when the file does not exist or cannot be read, or if *project_dir* was not given and the root of the current Git repository cannot be determined.

    If the file can be found and its syntax is correct, a dictionary is returned, containing a representation of the file contents according to the `tomllib` parser. `TOMLDecodeError` is raised if the syntax of the `TOML` document is invalid.
- `munge_oserror(`\
    `    exc: OSError`\
    `) -> dict[str, str | None]`\
    Process `OSError` exception *exc*.

    Process the `OSError` (or any of its subclasses) exception *exc* and return a dictionary with the attributes obtained from the instance.

    The keys and descriptions for the retrieved attributes are:
    - `errcodes: str`: the `errno` and `winerror` codes
    - `strerror: str`: the error message string, normalized (see below)
    - `filename1: str`: the first filename involved in the exception
    - `filename2: str`: the second filename involved in the exception

    Attributes are not guaranteed to exist, and in that case the stored value will be `None`, to make the dictionary easier to process, for examply for replacing missing values with a marker, etc.

    **NOTE**: the `errno` and `winerror` codes are combined with a slash character if both are present.

    **NOTE**: the returned error message is normalized if present. The first letter is uppercased and the final period (if any), removed.

    **NOTE**: depending on operation which caused the exception raising, there may be zero, one, or two paths involved.
- `resolve_version(`\
    `    template: str = '{tag}.post{distance}+{branch}{detached}.{rev}{dirty}'`\
    `) -> str | None`\
    Resolve the current version from VCS metadata.

    Return a version string generated from the repository VCS metadata, using the format string in *template*. If no metadata can be found, (e.g. the current working directory is not a repository, or it has no tags) then `None` is returned instead.

    A default value for *template* is used if it is not provided.

    The supported placeholders are:
    - `{tag}`: The most recent version tag, without a leading `v`.
    - `{distance}`: The number of commits since the tag.
    - `{branch}`: Current branch name, lowercased and sanitized, so it only contains characters in the `[a-z0-9]` set, replacing any other characters by `xxx`. It is an empty string if the repository is in the detached `HEAD` state.
    - `{detached}`: The string `detached` when the repository is in the detached `HEAD` state, otherwise it is an empty string.
    - `{rev}`: Abbreviated commit hash, without a leading `g`.
    - `{dirty}`: The string `.dirty` if the working tree has uncommitted changes, otherwise an empty string.

    All placeholders are optional, unused ones are silently ignored, but `KeyError` is raised if unknown placeholders are used in *template*.

    **NOTE**: with the default *template* the produced version string is fully compliant with the [`PyPA` version scheme](https://packaging.python.org/en/latest/specifications/version-specifiers/#version-scheme). All the supported placeholders produce fully compliant strings, too. To keep the resolved version string fully compliant, use only `+` as the local version specifier separator, and `.` as general separator.
- `run(`\
    `    command: collections.abc.Sequence[str],`\
    `    **kwargs: typing.Any`\
    `) -> subprocess.CompletedProcess[str]`\
    Run *command* with convenient defaults.

    Run *command*, using *kwargs* as arguments. Just a simple helper for `subprocess.run()` that provides convenient defaults.

    For that reason, the keyword arguments accepted in *kwargs* and the return value are the same ones used by `subprocess.run()` itself.
- `timestamp(`\
    `    template: str = '%Y%m%d_%H%M%S'`\
    `) -> str`\
    Produce a timestamp string from current local date and time.

    The function is actually a simple alias for `strftime()`, but using a default common `template` for the formatting string. Actually, any valid `strftime()` compatible formatting string can be used.
- `wait_for_keypress(`\
    `    prompt: str = '\nPress any key to continue...'`\
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

# Changelog
All notable changes to this project will be documented in this file.

This document is based on the [DervishD changelog specification](https://gist.github.com/DervishD/201c7a51c767c4703f732a2e29a7c3ea).

This project versioning scheme complies with the `Python Packaging Authority` [version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/) as defined by the `Python Packaging User Guide`.


## [Development]
### Fixed
- `post-checkout` hook no longer updates colophon file infinitely.


## [3.0.2]
### Fixed
- Improve automatic release tagging


## [3.0.1]
### Added
- Release-mode support for automatic version handling


## [3.0.0] 2026-04-30
The biggest breaking change in this major release is removing from the module as
much implicit behavior as possible, to avoid unexpected side effects. This means
that some constants have been removed or replaced by API calls, and some of the
side effects are no longer implicit.

### Removed
- `demo()` function
- Default `logger`
- Registration of customized logger into `logging.setLoggerClass`
- `excepthook()` no longer shows an error modal dialog
- `error()` function. It was not used anywhere so it is safe to remove
- All previously exported constants
- Implicit side-effects (the caller has to run them explicitly):
    - `excepthook()` installation
    - `sys.stdout` and `sys.stderr` reconfiguration into `utf-8` mode

### Changed
- Logging system is now more cooperative with `logging` module
- Logging of unhandled exceptions
- `munge_oserror()` now returns a dictionary, not a tuple
- `munge_oserror()` now uses `None` for any missing attribute instead of a mix
  of `None`, empty strings, markers, etc.
- `munge_oserror()` now removes ending period (if any) from `strerror`
- `munge_oserror()` no longer returns the exception type name
- `_ConvenienceLogger` is now exported and it is named `LegionLogger`
- Most hardcoded messages are now customizable
- Improved default exception hook, with customizable heading
- `wait_for_keypress()` is no longer automatically registered with `atexit`
- Documentation

### Added
- Unit test framework
- `LegionLogger` class
- `ensure_utf8_output()` function
- `format_message()` function
- `get_project_metadata()` function
- `excepthook()` exception chaining support


## [2.1.0] 2026-02-21
### Removed
- WFKStatuses enumeration type

### Changed
- Update changelog format
- Make `wait_for_keypress()` return `None`
- Improve `run()` call signature

### Added
- Package documentation is now auto-generated

### Fixed
- Minor code fixes and improvements
- Documentation improvements


## [2.0.1] 2026-01-26
### Fixed
- `README.md` was accidentally not in sync with current code


## [2.0.0] 2026-01-26
### Changed
- API change for `_CustomLogger.config()`. The keyword arguments for the logging
  files have been renamed. The `debugfile` argument is now `full_log_output`,
  since it does not have anything to do with debugging, but with the amount of
  logging levels dumped, it is a full, detailed log, not necessarily a debugging
  one. The `logfile` argument is now `main_log_output`, because it contains the
  logging levels an end user will typically be interested about. The `console`
  argument has not changed. Since they are keyword arguments this is of course a
  **breaking change**


## [1.2.0] 2026-01-17
### Changed
- Improved exception hook for win32 platform

### Added
- Changelog file
- Changelog specification

### Fixed
- Version handling
- Package structure
- Support for `help()`


## [1.1.0] 2025-10-23
### Changed
- Convert package to src-layout

### Added
- Demo facility

### Fixed
- Linting warnings


## [1.0.1] 2025-10-22
### Fixed
- Mark the package as type-annotated


## [1.0.0] 2025-10-22
### Added
- Custom, full-featured logging facility
- Simple but powerful command runner
- Simple credentials reader
- OSError processor and formatter for better error reporting
- Exception hook which produces good-looking output for unhandled exceptions
- Error reporting facility which produces good-looking error messages
- Useful run-time constants
- Timestamp string generator

[Development]: https://github.com/DervishD/legion/compare/v3.0.2...development
[3.0.2]: https://github.com/DervishD/legion/compare/v3.0.1...v3.0.2
[3.0.1]: https://github.com/DervishD/legion/compare/v3.0.0...v3.0.1
[3.0.0]: https://github.com/DervishD/legion/compare/v2.1.0...v3.0.0
[2.1.0]: https://github.com/DervishD/legion/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/DervishD/legion/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/DervishD/legion/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/DervishD/legion/compare/v1.1.1...v1.2.0
[1.1.0]: https://github.com/DervishD/legion/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/DervishD/legion/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/DervishD/legion/releases/tag/v1.0.0
# Changelog
All notable changes to this project will be documented in this file.

This document is based on the [DervishD changelog specification](https://gist.github.com/DervishD/201c7a51c767c4703f732a2e29a7c3ea).

This project versioning scheme complies with the `Python Packaging Authority` [version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/) as defined by the `Python Packaging User Guide`.

## [Development]

## [2.0.0] 2026-01-26
**Changed**
- API change for `_CustomLogger.config()`. The keyword arguments for the logging
  files have been renamed. The `debugfile` argument is now `full_log_output`,
  since it does not have anything to do with debugging, but with the amount of
  logging levels dumped, it is a full, detailed log, not necessarily a debugging
  one. The `logfile` argument is now `main_log_output`, because it contains the
  logging levels an end user will typically be interested about. The `console`
  argument has not changed. Since they are keyword arguments this is of course a
  **breaking change**

## [1.2.0] 2026-01-17
**Changed**
- Improved exception hook for win32 platform

**Added**
- Changelog file
- Changelog specification

**Fixed**
- Version handling
- Package structure
- Support for 'help()'

## [1.1.0] 2025-10-23
**Changed**
- Convert package to src-layout

**Added**
- Demo facility

**Fixed**
- Linting warnings

## [1.0.1] 2025-10-22
**Fixed**
- Mark the package as type-annotated

## [1.0.0] 2025-10-22
**Added**
- Custom, full-featured logging facility
- Simple but powerful command runner
- Simple credentials reader
- OSError processor and formatter for better error reporting
- Exception hook which produces good-looking output for unhandled exceptions
- Error reporting facility which produces good-looking error messages
- Useful run-time constants
- Timestamp string generator

[Development]: https://github.com/DervishD/legion/compare/v2.0.0...development
[2.0.0]: https://github.com/DervishD/legion/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/DervishD/legion/compare/v1.1.1...v1.2.0
[1.1.0]: https://github.com/DervishD/legion/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/DervishD/legion/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/DervishD/legion/releases/tag/v1.0.0
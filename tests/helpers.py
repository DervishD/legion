"""Helpers for test units."""
from enum import auto, StrEnum
import re
from typing import NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any


# pylint: disable-next=unused-variable
class LogPaths(NamedTuple):
    """Log paths abstraction."""  # noqa: D204
    main: Path
    full: Path


class LoggingFields(StrEnum):
    """Field names of a ParsedLogfile."""

    TIMESTAMPS = auto()
    LOGLEVELS = auto()
    FUNCNAMES = auto()
    MESSAGES = auto()


ParsedLogfile = dict[str, list[str | None]]
# pylint: disable-next=unused-variable
def parse_logfile(logfile: Path) -> ParsedLogfile:
    """Parse the contents of *logfile*.

    Each line is matched against `PARSE_REGEX` and split into the named
    fields defined in `LoggingFields`. The result is a `ParsedLogfile`
    dictionary, mapping each field name to a list of the corresponding
    parsed string values, one entry per line, preserving order.

    Raises `ValueError` if any line does not match `PARSE_REGEX`. The
    non-matching line is provided as argument to the exception.
    """
    logfile_parse_regex = re.compile(rf"""^
        (?:(?P<{LoggingFields.TIMESTAMPS}>\d{{8}}_\d{{6}}(?:\.\d{{4}})?+)(?:\ (?=.))?)
        (?:(?P<{LoggingFields.LOGLEVELS}>[A-Z]++)\ ++\|(?:\ (?=.))?)?+
        (?:(?P<{LoggingFields.FUNCNAMES}>[^\s(]++)\(\)(?:\ (?=.))?)?+
        (?P<{LoggingFields.MESSAGES}>.++)??
    $""", re.MULTILINE | re.VERBOSE)

    result: ParsedLogfile = {name: [] for name in logfile_parse_regex.groupindex}

    contents = logfile.read_text(encoding='utf-8')

    for line in contents.splitlines():
        match = logfile_parse_regex.match(line)
        if match is None:
            raise ValueError(line)
        match_groups = match.groupdict()
        for name in result:
            result[name].append(match_groups[name] or '')
    return result


# pylint: disable-next=unused-variable,too-few-public-methods
class CallableSpy[**P, R]:
    """Generic spy pattern for callables."""

    def __init__(self, target: Callable[P, R]) -> None:
        """."""
        self.target = target

        self.called: bool = False
        self.call_count: int = 0
        self.calls: list[tuple[R, tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """."""
        self.called = True
        self.call_count += 1

        retval = self.target(*args, **kwargs)
        self.calls.append((retval, args, kwargs))

        return retval

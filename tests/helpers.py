"""Helpers for test units."""
import re
from typing import NamedTuple, TYPE_CHECKING

import legion

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any

class LogPaths(NamedTuple):  # pylint: disable=unused-variable
    """Log paths abstraction."""  # noqa: D204
    log: Path
    trace: Path


LOGGING_NOISE_REGEX = re.compile(
    r'^\d{8}_\d{6}(?:\.\d{4})?+(?:[A-Z ]++\|)?+(?:[^(]++\(\))?+(?: (?P<message>.*))?$',
    re.MULTILINE,
)
def get_denoised_logfile_lines(logfile: Path) -> str:
    """Return *logfile* contents, de-noised.

    For each line, only the logging message is preserved. The timestamp,
    logging level, function name, separators, etc. are removed.

    Finally, since the final newline character is removed.
    """
    return LOGGING_NOISE_REGEX.sub(r'\g<message>', logfile.read_text(encoding=legion.UTF8)).removesuffix('\n')



def format_log_message(message: str, *, levelname:str = '', padding: str = '') -> list[str]:  # pylint: disable=unused-variable
    """Format *message* so it looks like a logging entry.

    The *levelname* is prepended to the message if provided, and in that
    case a separator is appended.

    If *padding* is provided, it is inserted before the message.
    """
    preamble = f'{levelname:<{legion.Logger.LEVELNAME_MAX_LEN}}{legion.Logger.LEVELNAME_SEPARATOR}' if levelname else ''
    return [f'{preamble}{padding}{line}'.rstrip() for line in message.split('\n')]


class CallableSpy[**P, R]:  # pylint: disable=unused-variable, too-few-public-methods
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

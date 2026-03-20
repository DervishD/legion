"""."""
import atexit
import contextlib
from importlib.metadata import PackageNotFoundError, version
from inspect import isclass, isfunction
import logging
from pathlib import Path

import legion

__all__ = []

DEMO_BANNER = '{} package v{}\n'
DEMO_TIMESTAMP_FMT = f'{{}}() {legion.ARROW_R} {{}}\n'
DEMO_CONSTANT_FMT = f'{{:┄<{{}}}}{legion.ARROW_R} ⟦{{}}⟧'


def demo() -> None:
    """Demonstrate package features."""
    atexit.register(logging.shutdown)

    logger = legion.get_logger(__name__)
    with contextlib.suppress(PackageNotFoundError):
        self_name = __package__ or str(Path(__file__).resolve().parent)
        logger.info(DEMO_BANNER.format(self_name, version(self_name)))

    logger.info(DEMO_TIMESTAMP_FMT.format(legion.timestamp.__name__, legion.timestamp()))

    width = 0
    constants: dict[str, str] = {}
    for name in legion.__all__:
        obj = vars(legion)[name]
        if name.startswith('_') or not name.isupper() or isfunction(obj) or isclass(obj):
            continue
        width = max(width, len(name) + 1)
        constants[name] = obj

    for constant, value in constants.items():
        logger.info(DEMO_CONSTANT_FMT.format(constant, width, value))



demo()

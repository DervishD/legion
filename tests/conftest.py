"""Configuration file for pytest."""
import logging
import sys
from typing import TYPE_CHECKING

import pytest

import legion
from tests.helpers import LoggingPaths

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path


@pytest.fixture
# pylint: disable-next=unused-variable
def logging_paths(tmp_path: Path) -> Generator[LoggingPaths]:
    """Generate temporary paths for logging files in *tmp_path*."""
    main_output_path = tmp_path / 'log.txt'
    full_output_path = tmp_path / 'trace.txt'

    yield LoggingPaths(main_output_path, full_output_path)

    main_output_path.unlink()
    full_output_path.unlink()


@pytest.fixture
# pylint: disable-next=unused-variable,redefined-outer-name
def logger(logging_paths: LoggingPaths) -> Generator[legion.Logger]:
    """Set up and return a logger, configured using *log_paths*."""
    logger_instance = legion.get_logger(__name__)

    logger_instance.config(main_log_output=logging_paths.main, full_log_output=logging_paths.full)

    yield logger_instance

    logging.shutdown()


@pytest.fixture
# pylint: disable-next=unused-variable
def evict_module(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """Evict *module_name* from the currently loaded modules.

    It is actually a factory, and returns the real evictor, which then
    can be called to evict the module. This simplifies parameter passing
    for the fixture.
    """
    def module_evictor(module_name: str) -> None:
        monkeypatch.delitem(sys.modules, module_name, raising=False)
    return module_evictor

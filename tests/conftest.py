"""Configuration file for pytest."""
import logging
from typing import TYPE_CHECKING

import pytest

from legion import get_logger, LegionLogger

from .helpers import LoggingPaths

if TYPE_CHECKING:
    from collections.abc import Generator
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
def logger(logging_paths: LoggingPaths) -> Generator[LegionLogger]:
    """Set up and return a logger, configured using *log_paths*."""
    logger_instance = get_logger(__name__)

    logger_instance.config(main_log_output=logging_paths.main, full_log_output=logging_paths.full)

    yield logger_instance

    logging.shutdown()

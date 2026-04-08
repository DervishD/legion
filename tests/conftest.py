"""Configuration file for pytest."""
import logging
from typing import TYPE_CHECKING

import pytest

import legion
from tests.helpers import LogPaths

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture
# pylint: disable-next=unused-variable
def log_paths(tmp_path: Path) -> Generator[LogPaths]:
    """Generate temporary paths for logging files in *tmp_path*."""
    main_output_path = tmp_path / 'log.txt'
    full_output_path = tmp_path / 'trace.txt'

    yield LogPaths(main_output_path, full_output_path)

    main_output_path.unlink()
    full_output_path.unlink()


@pytest.fixture
# pylint: disable-next=unused-variable,redefined-outer-name
def logger(log_paths: LogPaths) -> Generator[legion.Logger]:
    """Set up and return a logger, configured using *log_paths*."""
    logger_instance = legion.get_logger(__name__)

    logger_instance.config(main_log_output=log_paths.main, full_log_output=log_paths.full)

    yield logger_instance

    logging.shutdown()

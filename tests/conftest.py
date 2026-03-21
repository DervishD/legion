#! /usr/bin/env python3
"""Configuration file for pytest."""
from typing import TYPE_CHECKING

import pytest

from tests.helpers import LogPaths

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture
def log_paths(tmp_path: Path) -> Generator[LogPaths]:  # pylint: disable=unused-variable
    """Generate temporary paths for logging files in *tmp_path*."""
    main_output_path = tmp_path / 'log.txt'
    full_output_path = tmp_path / 'trace.txt'

    yield LogPaths(main_output_path, full_output_path)

    main_output_path.unlink()
    full_output_path.unlink()

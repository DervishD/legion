"""Test units for `timestamp()` function."""
from typing import TYPE_CHECKING

from legion import timestamp

from .helpers import CallableSpy

if TYPE_CHECKING:
    import pytest


# pylint: disable-next=unused-variable
def test_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `timestamp()` function."""
    format_string = 'Example timestamp template, will be ignored'
    time_string = '2084-07-07 06:54:54.9'  # TMA-1

    def mock_strftime(_: str) -> str:
        return time_string

    strftime_spy = CallableSpy(mock_strftime)

    monkeypatch.setitem(timestamp.__globals__, 'strftime', strftime_spy)

    timestamp()
    timestamp(format_string)

    assert strftime_spy.called
    assert strftime_spy.call_count == 2  # noqa: PLR2004
    assert strftime_spy.calls == [(time_string, ('%Y%m%d_%H%M%S',), {}),(time_string, (format_string,), {})]

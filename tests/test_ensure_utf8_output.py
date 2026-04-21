"""Test units for `ensure_utf8_output()`."""
import sys
from typing import TYPE_CHECKING

from legion import ensure_utf8_output

from .helpers import CallableSpy

if TYPE_CHECKING:
    import pytest


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_reconfigure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test decorator baseline."""
    def mock_reconfigure(**_: object) -> None:
        pass

    class MockOutputStream:  # pylint: disable=missing-class-docstring
        def __init__(self) -> None:
            self.reconfigure = CallableSpy(mock_reconfigure)

    mock_stdout = MockOutputStream()
    mock_stderr = MockOutputStream()
    monkeypatch.setattr(sys, 'stdout', mock_stdout)
    monkeypatch.setattr(sys, 'stderr', mock_stderr)

    @ensure_utf8_output
    def mock_function() -> None:
        pass

    mock_function()
    assert mock_stdout.reconfigure.called
    assert mock_stderr.reconfigure.called
    assert mock_stdout.reconfigure.call_count == 1
    assert mock_stderr.reconfigure.call_count == 1
    assert mock_stdout.reconfigure.calls == [(None, (), {'encoding': 'utf-8'})]
    assert mock_stderr.reconfigure.calls == [(None, (), {'encoding': 'utf-8'})]


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_missing_reconfigure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test decorator on streams without `reconfigure()`."""
    monkeypatch.setattr(sys, 'stdout', object())
    monkeypatch.setattr(sys, 'stderr', object())

    @ensure_utf8_output
    def mock_function() -> None:
        pass

    mock_function()


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_none_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test decorator on streams which are `None`."""
    monkeypatch.setattr(sys, 'stdout', None)
    monkeypatch.setattr(sys, 'stderr', None)

    @ensure_utf8_output
    def mock_function() -> None:
        pass

    mock_function()


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_decorator_args() -> None:
    """Test proper forward of arguments by decorator."""
    @ensure_utf8_output
    def mock_function(mock_x: int, mock_y: int, *, reverse: bool = False) -> tuple[int, int]:
        return (mock_y, mock_x) if reverse else (mock_x, mock_y)

    assert mock_function(42, 73) == (42, 73)
    assert mock_function(42, 73, reverse=True) == (73, 42)


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_decorator_retval() -> None:
    """Test proper forward of return value by decorator."""
    retval = 42

    @ensure_utf8_output
    def mock_function() -> int:
        return retval

    assert mock_function() == retval


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_decorator_transparency() -> None:
    """Test proper forward of metadata by decorator."""
    @ensure_utf8_output
    def mock_function() -> None:
        """Mock docstring."""

    assert mock_function.__name__ == 'mock_function'
    assert mock_function.__doc__ == 'Mock docstring.'
    assert getattr(mock_function, '__wrapped__', None) is not None

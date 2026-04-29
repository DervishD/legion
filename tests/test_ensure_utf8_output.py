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

    test_stdout = MockOutputStream()
    test_stderr = MockOutputStream()
    monkeypatch.setattr(sys, 'stdout', test_stdout)
    monkeypatch.setattr(sys, 'stderr', test_stderr)

    @ensure_utf8_output
    def example_function() -> None:
        pass

    example_function()
    assert test_stdout.reconfigure.called
    assert test_stderr.reconfigure.called
    assert test_stdout.reconfigure.call_count == 1
    assert test_stderr.reconfigure.call_count == 1
    assert test_stdout.reconfigure.calls == [(None, (), {'encoding': 'utf-8'})]
    assert test_stderr.reconfigure.calls == [(None, (), {'encoding': 'utf-8'})]


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_missing_reconfigure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test decorator on streams without `reconfigure()`."""
    monkeypatch.setattr(sys, 'stdout', object())
    monkeypatch.setattr(sys, 'stderr', object())

    @ensure_utf8_output
    def example_function() -> None:
        pass

    example_function()


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_none_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test decorator on streams which are `None`."""
    monkeypatch.setattr(sys, 'stdout', None)
    monkeypatch.setattr(sys, 'stderr', None)

    @ensure_utf8_output
    def example_function() -> None:
        pass

    example_function()


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_decorator_args() -> None:
    """Test proper forward of arguments by decorator."""
    @ensure_utf8_output
    def example_function(x: int, y: int, *, reverse: bool = False) -> tuple[int, int]:
        return (y, x) if reverse else (x, y)

    assert example_function(42, 73) == (42, 73)
    assert example_function(42, 73, reverse=True) == (73, 42)


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_decorator_retval() -> None:
    """Test proper forward of return value by decorator."""
    retval = 42

    @ensure_utf8_output
    def example_function() -> int:
        return retval

    assert example_function() == retval


# pylint: disable-next=unused-variable
def test_ensure_utf8_output_decorator_transparency() -> None:
    """Test proper forward of metadata by decorator."""
    @ensure_utf8_output
    def example_function() -> None:
        """Example docstring."""

    assert example_function.__name__ == 'example_function'
    assert example_function.__doc__ == 'Example docstring.'
    assert getattr(example_function, '__wrapped__', None) is not None

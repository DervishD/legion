#! /usr/bin/env python3
"""Test suite for `main()` function."""
import pytest

from legion import (
    _has_attached_console,  # pyright: ignore[reportPrivateUsage]
    _is_attached_console_transient,  # pyright: ignore[reportPrivateUsage]
    wait_for_keypress,
)

from .helpers import CallableSpy


def mock_wait_for_keypress(
    monkeypatch: pytest.MonkeyPatch, *,
    prompt: str | None = None,
    has_attached_console: bool,
    is_attached_console_transient: bool,
) -> CallableSpy[[], bytes]:
    """Mock `wait_for_keypress()` calls."""
    getch_spy = CallableSpy(lambda: b'')

    monkeypatch.setitem(wait_for_keypress.__globals__, 'getch', getch_spy)
    monkeypatch.setitem(wait_for_keypress.__globals__,
        _has_attached_console.__name__,
        lambda: has_attached_console,
    )
    monkeypatch.setitem(wait_for_keypress.__globals__,
        _is_attached_console_transient.__name__,
        lambda: is_attached_console_transient,
    )

    wait_for_keypress(*(() if prompt is None else (prompt,)))

    return getch_spy


@pytest.mark.parametrize(('has_attached_console', 'is_attached_console_transient', 'expected'), [
    pytest.param(False, None, False, id='test_no_wait_for_keypress_no_console_attached'),
    pytest.param(True, False, False, id='test_no_wait_for_keypress_no_transient_console'),
    pytest.param(True, True, True, id='test_do_wait_for_keypress'),
])
def test_wait_for_keypress(  # pylint: disable=unused-variable
    monkeypatch: pytest.MonkeyPatch, *,
    has_attached_console: bool, is_attached_console_transient: bool,
    expected: bool) -> None:
    """Test that the waiting happens only when it should."""
    getch_spy = mock_wait_for_keypress(
        monkeypatch,
        has_attached_console=has_attached_console,
        is_attached_console_transient=is_attached_console_transient,
    )

    assert getch_spy.called is expected


# pylint: disable-next=unused-variable
def test_customized_prompt(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Test customized prompt output."""
    custom_prompt = 'This is a custom prompt!'
    mock_wait_for_keypress(monkeypatch,
        prompt=custom_prompt,
        has_attached_console=True,
        is_attached_console_transient=True,
    )
    output = capsys.readouterr().out

    assert output == custom_prompt

"""Test platform-specific behavior."""
import importlib
from typing import TYPE_CHECKING

import pytest

import legion

if TYPE_CHECKING:
    from collections.abc import Callable

MODULE_NAME = legion.__name__
WIN32_ONLY_SYMBOLS = (
    'byref', 'c_uint', 'create_unicode_buffer', 'Structure', 'windll',  # From ctypes
    'BYTE', 'DWORD', 'LPWSTR', '_MAX_PATH_LEN', 'WORD',  # From ctypes.wintypes
    'get_osfhandle', 'getch',  # From msvcrt
    '_has_attached_console', '_is_attached_console_transient',  # From legion
)


# pylint: disable-next=unused-variable
def test_platform_win32(monkeypatch: pytest.MonkeyPatch, evict_module: Callable[[str], None]) -> None:
    """Test that the module loads correctly on win32 platform."""
    evict_module(MODULE_NAME)
    monkeypatch.setattr('sys.platform', 'win32')
    module = importlib.import_module(MODULE_NAME)

    for symbol in WIN32_ONLY_SYMBOLS:
        assert hasattr(module, symbol)


# pylint: disable-next=unused-variable
def test_platform_non_win32(monkeypatch: pytest.MonkeyPatch, evict_module: Callable[[str], None]) -> None:
    """Test that SystemExit is raised on non-win32 platforms."""
    evict_module(MODULE_NAME)
    monkeypatch.setattr('sys.platform', 'mock_platform')
    module = importlib.import_module(MODULE_NAME)

    for symbol in WIN32_ONLY_SYMBOLS:
        assert not hasattr(module, symbol)

    with pytest.raises(NotImplementedError):
        module.wait_for_keypress()

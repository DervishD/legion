"""Test platform-specific behavior."""
import importlib
import sys

import pytest

WIN32_ONLY_SYMBOLS = (
    'byref', 'c_uint', 'create_unicode_buffer', 'Structure', 'windll',  # From ctypes
    'BYTE', 'DWORD', 'LPWSTR', '_MAX_PATH_LEN', 'WORD',  # From ctypes.wintypes
    'get_osfhandle', 'getch',  # From msvcrt
    '_has_attached_console', '_is_attached_console_transient',  # From legion
)


# pylint: disable-next=unused-variable
def test_platform_win32(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the module loads correctly on win32 platform."""
    monkeypatch.delitem(sys.modules, 'legion', raising=False)
    monkeypatch.setattr('sys.platform', 'win32')
    module = importlib.import_module('legion')

    for symbol in WIN32_ONLY_SYMBOLS:
        assert hasattr(module, symbol)


# pylint: disable-next=unused-variable
def test_platform_non_win32(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that SystemExit is raised on non-win32 platforms."""
    monkeypatch.delitem(sys.modules, 'legion', raising=False)
    monkeypatch.setattr('sys.platform', 'mock_platform')
    module = importlib.import_module('legion')

    for symbol in WIN32_ONLY_SYMBOLS:
        assert not hasattr(module, symbol)

    with pytest.raises(NotImplementedError):
        module.wait_for_keypress()

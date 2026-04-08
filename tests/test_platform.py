"""Test platform-specific behavior."""
import importlib
import sys

import pytest

import legion

MODULE_NAME = legion.__name__
WIN32_ONLY_SYMBOLS = (
    'byref', 'c_uint', 'create_unicode_buffer', 'Structure', 'windll',  # From ctypes
    'BYTE', 'DWORD', 'LPWSTR', '_MAX_PATH_LEN', 'WORD',  # From ctypes.wintypes
    'get_osfhandle', 'getch',  # From msvcrt
    '_has_attached_console', '_is_attached_console_transient',  # From legion
)


@pytest.fixture(autouse=True)
# pylint: disable-next=unused-variable
def evict_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the module is evicted before each test."""
    monkeypatch.delitem(sys.modules, MODULE_NAME, raising=False)


# pylint: disable-next=unused-variable
def test_loads_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the module loads correctly on win32 platform."""
    monkeypatch.setattr('sys.platform', 'win32')

    module = importlib.import_module(MODULE_NAME)

    for symbol in WIN32_ONLY_SYMBOLS:
        assert hasattr(module, symbol)


# pylint: disable-next=unused-variable
def test_rejects_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that SystemExit is raised on non-win32 platforms."""
    monkeypatch.setattr('sys.platform', 'mock_platform')

    module = importlib.import_module(MODULE_NAME)

    for symbol in WIN32_ONLY_SYMBOLS:
        assert not hasattr(module, symbol)

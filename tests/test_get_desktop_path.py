"""Test units for `get_desktop_path()` function."""
from ctypes.wintypes import LPWSTR
from pathlib import PurePosixPath, PureWindowsPath
import sys
from typing import Self, TYPE_CHECKING

from legion import get_desktop_path, windll

if TYPE_CHECKING:
    import pytest


# pylint: disable-next=unused-variable
def test_get_desktop_path_win32(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test behavior of `get_desktop_path()` in `win32` platform."""
    mock_desktop_path = PureWindowsPath('C:\\Users\\mock_user\\mock_Desktop')
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setitem(get_desktop_path.__globals__, 'Path', PureWindowsPath)

    mock_path = LPWSTR(str(mock_desktop_path))
    monkeypatch.setitem(get_desktop_path.__globals__, 'LPWSTR', lambda: mock_path)
    def noop (*_: object) -> int:
        return 0
    monkeypatch.setattr(windll.shell32, 'SHGetKnownFolderPath', noop)
    monkeypatch.setattr(windll.ole32, 'CoTaskMemFree', noop)

    assert get_desktop_path() == mock_desktop_path

    mock_path.value = None
    assert get_desktop_path() is None


# pylint: disable-next=unused-variable
def test_get_desktop_path_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test behavior of `get_desktop_path()` in `linux*` platforms."""
    class MockPurePosixPath(PurePosixPath):  # pylint: disable=missing-class-docstring
        MOCK_HOME = '/home/mock_user'
        @classmethod
        def home(cls) -> Self:  # pylint: disable=missing-function-docstring
            return cls(cls.MOCK_HOME)
    monkeypatch.setattr(sys, 'platform', 'linux-generic')
    monkeypatch.setitem(get_desktop_path.__globals__, 'Path', MockPurePosixPath)

    mock_desktop_path = MockPurePosixPath.home() / 'mock_Desktop'
    monkeypatch.setenv('XDG_DESKTOP_DIR', str(mock_desktop_path))
    assert get_desktop_path() == mock_desktop_path

    mock_desktop_path = MockPurePosixPath.home() / 'Desktop'
    monkeypatch.delenv('XDG_DESKTOP_DIR')
    assert get_desktop_path() == mock_desktop_path


# pylint: disable-next=unused-variable
def test_get_desktop_path_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test behavior of `get_desktop_path()` in `darwin` platform."""
    class MockPurePosixPath(PurePosixPath):  # pylint: disable=missing-class-docstring
        MOCK_HOME = '/home/mock_user'
        @classmethod
        def home(cls) -> Self:  # pylint: disable=missing-function-docstring
            return cls(cls.MOCK_HOME)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setitem(get_desktop_path.__globals__, 'Path', MockPurePosixPath)

    mock_desktop_path = MockPurePosixPath.home() / 'Desktop'
    monkeypatch.delenv('XDG_DESKTOP_DIR', raising=False)
    assert get_desktop_path() == mock_desktop_path

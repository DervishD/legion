"""Test units for `load_pyproject()` function."""
from pathlib import Path
import tomllib

import pytest

from legion import load_pyproject

MOCK_TOML = '[project]\nname = "myproject"\nversion = "1.0.0"\n'

# pylint: disable-next=unused-variable
def test_load_pyproject_baseline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test `load_pyproject()` baseline."""
    monkeypatch.setattr('legion.git_repository_root', lambda: tmp_path)
    (tmp_path / 'pyproject.toml').write_text(MOCK_TOML, encoding='utf-8')

    result = load_pyproject()

    assert result == {'project': {'name': 'myproject', 'version': '1.0.0'}}


# pylint: disable-next=unused-variable
def test_load_pyproject_with_project_dir(tmp_path: Path) -> None:
    """Test `load_pyproject()` with provided *project_dir*."""
    (tmp_path / 'pyproject.toml').write_text(MOCK_TOML, encoding='utf-8')

    result = load_pyproject(project_dir=tmp_path)

    assert result == {'project': {'name': 'myproject', 'version': '1.0.0'}}


# pylint: disable-next=unused-variable
def test_load_pyproject_arg_default_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test `load_pyproject()` with overridden *project_dir*."""
    (tmp_path / 'pyproject.toml').write_text(MOCK_TOML, encoding='utf-8')
    monkeypatch.setattr('legion.git_repository_root', lambda: tmp_path / 'nonexistent')

    result = load_pyproject(project_dir=tmp_path)

    assert result == {'project': {'name': 'myproject', 'version': '1.0.0'}}


# pylint: disable-next=unused-variable
def test_load_pyproject_no_project_dir_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `load_pyproject()` without any *project_dir*."""
    monkeypatch.setattr('legion.git_repository_root', lambda: None)

    assert load_pyproject() is None


# pylint: disable-next=unused-variable
def test_load_pyproject_not_found(tmp_path: Path) -> None:
    """Test `load_pyproject()` when the file does not exist."""
    assert load_pyproject(project_dir=tmp_path) is None


# pylint: disable-next=unused-variable
def test_returns_none_on_permission_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test `load_pyproject()` when the file cannot be read."""
    def mock_read_text(*_a: object, **_kw: object) -> None:
        raise PermissionError
    monkeypatch.setattr(Path, 'read_text', mock_read_text)
    (tmp_path / 'pyproject.toml').write_text(MOCK_TOML, encoding='utf-8')

    assert load_pyproject(project_dir=tmp_path) is None


# pylint: disable-next=unused-variable
def test_raises_on_invalid_toml(tmp_path: Path) -> None:
    """Test `load_pyproject()` when the file has invalid syntax."""
    (tmp_path / 'pyproject.toml').write_text('this is : not [ valid toml', encoding='utf-8')
    with pytest.raises(tomllib.TOMLDecodeError):
        load_pyproject(project_dir=tmp_path)

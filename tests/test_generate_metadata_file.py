"""Test units for `generate_metadata_file()` function."""
from copy import deepcopy
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from legion import generate_metadata_file

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    import pytest


MOCK_PROJECT_ROOT = Path('/mock/project_root')
MOCK_PROJECT_NAME = 'mock_project'
MOCK_PYPROJECT = {'project': {'name': MOCK_PROJECT_NAME}, 'mock_key': 'mock_value'}
MOCK_VERSION = '0.42.73.137'

def mock_git_repository_root(*_: object) -> Path:
    """Mock `git_repository_root()`."""
    return MOCK_PROJECT_ROOT

def mock_load_pyproject(*_: object) -> dict[str, Any]:
    """Mock `load_pyproject()`."""
    return deepcopy(MOCK_PYPROJECT)

def mock_resolve_version(*_: object) -> str:
    """Mock `resolve_version()`."""
    return MOCK_VERSION

def mock_output_path_factory(root: Path, *_: object) -> Callable[[dict[str, Any]], Path]:
    """Mock output path factory... factory."""
    def wrapped(m: dict[str, Any]) -> Path:
        return root / f'{m['project']['name']}_{m['project']['version']}.{m['mock_key']}'
    return wrapped


def return_none(*_: object) -> None:
    """Monkeypatch helper to return `None`."""


# pylint: disable-next=unused-variable
def test_generate_metadata_baseline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test `generate_metadata()` baseline."""
    mock_custom_suffix = 'mock_custom_suffix'

    template = dedent("""
        project_root = {project_root!r}
        project_name = {project[name]!r}
        project_version = {project[version]!r}
        mock_key = {mock_key!r}
        custom_suffix = {custom_suffix!r}
    """).lstrip()

    expected = dedent(f"""
        project_root = {MOCK_PROJECT_ROOT!r}
        project_name = {MOCK_PROJECT_NAME!r}
        project_version = {MOCK_VERSION!r}
        mock_key = {MOCK_PYPROJECT['mock_key']!r}
        custom_suffix = {mock_custom_suffix!r}
    """).lstrip()

    monkeypatch.setattr('legion.git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.resolve_version', mock_resolve_version)

    extra_metadata = {'custom_suffix': mock_custom_suffix}
    output_file = generate_metadata_file(mock_output_path_factory(tmp_path), template, extra_metadata)
    assert output_file is not None
    assert output_file == tmp_path / f'{MOCK_PROJECT_NAME}_{MOCK_VERSION}.{MOCK_PYPROJECT['mock_key']}'
    assert output_file.is_file()
    assert output_file.read_text(encoding='utf-8') == expected


# pylint: disable-next=unused-variable
def test_generate_metadata_project_root_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that `None` is returned when it should."""
    monkeypatch.setattr('legion.git_repository_root', return_none)
    assert generate_metadata_file(mock_output_path_factory(tmp_path), '') is None

    monkeypatch.setattr('legion.git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion.load_pyproject', return_none)
    assert generate_metadata_file(mock_output_path_factory(tmp_path), '') is None

    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.resolve_version', return_none)
    assert generate_metadata_file(mock_output_path_factory(tmp_path), '') is None

    monkeypatch.setattr('legion.resolve_version', mock_resolve_version)
    assert generate_metadata_file(return_none, '') is None


# # pylint: disable-next=unused-variable
def test_generate_metadata_project_root_injection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that project root is injected when it should."""
    monkeypatch.setattr('legion.git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.resolve_version', mock_resolve_version)

    output_file = generate_metadata_file(mock_output_path_factory(tmp_path), '{project_root!s}')
    assert output_file is not None
    assert output_file.is_file()
    assert output_file.read_text(encoding='utf-8') == str(MOCK_PROJECT_ROOT)

    output_file.unlink()

    extra_metadata = {'project_root': 'overriden'}
    output_file = generate_metadata_file(mock_output_path_factory(tmp_path), '{project_root!s}', extra_metadata)
    assert output_file is not None
    assert output_file.is_file()
    assert output_file.read_text(encoding='utf-8') == 'overriden'


# pylint: disable-next=unused-variable
def test_generate_metadata_version_injection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that resolved version is injected when it should."""
    monkeypatch.setattr('legion.git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.resolve_version', mock_resolve_version)

    output_file = generate_metadata_file(mock_output_path_factory(tmp_path), '{project[version]}')
    assert output_file is not None
    assert output_file.is_file()
    assert output_file.read_text(encoding='utf-8') == MOCK_VERSION

    output_file.unlink()

    extra_metadata = {'project': {'version': 'original'}}
    output_file = generate_metadata_file(mock_output_path_factory(tmp_path), '{project[version]}', extra_metadata)
    assert output_file is not None
    assert output_file.is_file()
    assert output_file.read_text(encoding='utf-8') == 'original'


# pylint: disable-next=unused-variable
def test_generate_metadata_extra_injection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that extra metadata is injected when it should."""
    output_path_factory_received_metadata: dict[str, Any] = {}
    def _mock_output_path_factory(m: dict[str, Any]) -> Path:
        output_path_factory_received_metadata.update(m)
        return tmp_path / 'mock_output_file.txt'

    monkeypatch.setattr('legion.git_repository_root', mock_git_repository_root)
    monkeypatch.setattr('legion.load_pyproject', mock_load_pyproject)
    monkeypatch.setattr('legion.resolve_version', mock_resolve_version)

    extra_metadata = {'project': {'name': 'overriden'}, 'extra_key': 'extra_value'}
    output_file = generate_metadata_file(_mock_output_path_factory, '{project[name]} {extra_key}', extra_metadata)
    assert output_file is not None
    assert output_file.is_file()
    assert output_file.read_text(encoding='utf-8') == 'overriden extra_value'
    assert output_path_factory_received_metadata['project']['name'] == 'overriden'
    assert output_path_factory_received_metadata['extra_key'] == 'extra_value'

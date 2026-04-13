"""Test units for `get_credentials()` function."""
from annotationlib import Format
import inspect
from pathlib import Path
from typing import Any

import pytest

from legion import get_credentials

S = 'section'
K = 'key'
V = 'value'


@pytest.mark.parametrize(('contents', 'expected'), [
    pytest.param('', {}, id='test_get_credentials_empty_contents'),
    pytest.param('this is not [ valid toml !!!', None, id='test_get_credentials_invalid_contents'),
    pytest.param(
        f'[{S}]\n{K}1 = "{V}1"\n{K}2 = "{V}2"',
        {S: {f'{K}1': f'{V}1', f'{K}2': f'{V}2'}},
        id='test_get_credentials_single_section',
    ),
    pytest.param(
        f'[{S}1]\n{K}11 = "{V}11"\n{K}12 = "{V}12"\n[{S}2]\n{K}21 = "{V}21"\n{K}22 = "{V}22"',
        {f'{S}1': {f'{K}11': f'{V}11', f'{K}12': f'{V}12'}, f'{S}2': {f'{K}21': f'{V}21', f'{K}22': f'{V}22'}},
        id='test_get_credentials_multiple_sections',
    ),
])
# pylint: disable-next=unused-variable
def test_get_credentials_returns_parsed_toml(
    tmp_path: Path,
    contents: str,
    expected: dict[str, Any],
) -> None:
    """Test contents processing."""
    creds_file = tmp_path / 'mock_credentials.toml'
    creds_file.write_text(contents, encoding='utf-8')

    result = get_credentials(creds_file)

    assert result == expected


# pylint: disable-next=unused-variable
def test_get_credentials_oserror(tmp_path: Path) -> None:
    """Test that `None` is returned if `OSError` is raised."""
    mock_credentials_path = tmp_path / 'mock_credentials_does_not_exist'
    result = get_credentials(mock_credentials_path)

    assert not mock_credentials_path.is_file()
    assert result is None


# pylint: disable-next=unused-variable
def test_get_credentials_default_path() -> None:
    """Test that the default value is correct."""
    signature = inspect.signature(get_credentials, annotation_format=Format.STRING)

    assert signature.parameters['credentials_path'].default == Path.home() / '.credentials'

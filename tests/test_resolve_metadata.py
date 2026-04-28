"""Test units for `resolve_metadata()`."""
from copy import deepcopy
from typing import TYPE_CHECKING

import pytest

from legion import resolve_metadata

if TYPE_CHECKING:
    from typing import Any


SUBTABLE = 'subtable.dict'
@pytest.fixture
# pylint: disable-next=unused-variable
def metadata() -> dict[str, Any]:
    """Return a fresh copy of the sample metadata."""
    return {
        'toplevel_string': 'There was a button. I pushed it.',
        'toplevel_dict': {'mock_key': 'mock_value'},
        f'{SUBTABLE.split('.', maxsplit=1)[0]}': {
            f'{SUBTABLE.split('.', maxsplit=1)[1]}': {
                'string': 'mock_string',
                'int': 42,
                'float': 73.109,
                'bool': False,
                'eval': '!!len({subtable[dict][string]!r})',
                'eval_type_preserve': '!![42, 73, 109]',
                'simple_interpolation': '{subtable[dict][eval]}/{toplevel_string}',
                'chained_interpolation': '{subtable[dict][simple_interpolation]}/{toplevel_dict[mock_key]}',
                'list': [
                    42,
                    'mock_string_in_list',
                    {'int_in_dict_in_list': 42, 'string_in_dict_in_list': 'mock_string_in_dict_in_list'},
                ],
                'dict': {
                    'int_in_dict': 42,
                    'string_in_dict': 'mock_string_in_dict',
                    'list_in_dict': [42, 'mock_string_in_list_in_dict'],
                },
                'empty_list': [],
                'empty_dict': {},
            },
        },
    }


EXPECTED = {
    'toplevel_string': 'There was a button. I pushed it.',
    'toplevel_dict': {'mock_key': 'mock_value'},
    f'{SUBTABLE.split('.', maxsplit=1)[0]}': {
        f'{SUBTABLE.split('.', maxsplit=1)[1]}': {
            'string': 'mock_string',
            'int': 42,
            'float': 73.109,
            'bool': False,
            'eval': 11,
            'eval_type_preserve': [42, 73, 109],
            'simple_interpolation': '11/There was a button. I pushed it.',
            'chained_interpolation': '11/There was a button. I pushed it./mock_value',
            'list': [
                42,
                'mock_string_in_list',
                {'int_in_dict_in_list': 42, 'string_in_dict_in_list': 'mock_string_in_dict_in_list'},
            ],
            'dict': {
                'int_in_dict': 42,
                'string_in_dict': 'mock_string_in_dict',
                'list_in_dict': [42, 'mock_string_in_list_in_dict'],
            },
            'empty_list': [],
            'empty_dict': {},
        },
    },
}


# pylint: disable-next=unused-variable,redefined-outer-name
def test_resolve_metadata_do_not_mutate(metadata: dict[str, Any]) -> None:
    """Test that original *metadata* is not mutated."""
    original = deepcopy(metadata)
    resolve_metadata(metadata, SUBTABLE)
    assert metadata == original


# pylint: disable-next=unused-variable,redefined-outer-name
def test_resolve_metadata_invalid_table_raises(metadata: dict[str, Any]) -> None:
    """Test that invalid *table* raises `KeyError`."""
    with pytest.raises(KeyError):
        resolve_metadata(metadata, f'__{SUBTABLE}__')


# pylint: disable-next=unused-variable,redefined-outer-name
def test_resolve_metadata_baseline(metadata: dict[str, Any]) -> None:
    """Test `resolve_metadata()` functionality."""
    resolved = resolve_metadata(metadata, SUBTABLE)
    assert resolved == EXPECTED


# pylint: disable-next=unused-variable,redefined-outer-name
def test_resolve_metadata_unresolvable_placeholder(metadata: dict[str, Any]) -> None:
    """Test that unresolvable placeholders raise `KeyError`."""
    metadata['subtable']['dict']['unresolvable'] = '{unresolvable[placeholder]}'
    with pytest.raises(KeyError):
        resolve_metadata(metadata, SUBTABLE)

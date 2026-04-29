"""Test units for `format_oserror()` function."""
import pytest

from legion import format_oserror


@pytest.mark.parametrize(('munged', 'exc', 'expected'), [
    pytest.param(
        {
            'errcodes': 'EXAMPLE_ERRNO/WinError42',
            'strerror': 'Example error message string',
            'filename1': 'example_filename1',
            'filename2': 'example_filename2',
        },
        OSError(),
        (
            "OSError [EXAMPLE_ERRNO/WinError42] doing something 'example_filename1' -> 'example_filename2'.\n"
            'Example error message string.'
        ),
        id='test_format_oserror_baseline',
    ),
    pytest.param(
        {
            'errcodes': 'EXAMPLE_ERRNO/WinError42',
            'strerror': 'Example error message string',
            'filename1': 'example_filename1',
            'filename2': None,
        },
        OSError(),
        (
            "OSError [EXAMPLE_ERRNO/WinError42] doing something 'example_filename1'.\n"
            'Example error message string.'
        ),
        id='test_format_oserror_no_filename2',
    ),
    pytest.param(
        {
            'errcodes': 'EXAMPLE_ERRNO/WinError42',
            'strerror': 'Example error message string',
            'filename1': 'example_filename1',
            'filename2': None,
        },
        PermissionError(),
        (
            "OS.PermissionError [EXAMPLE_ERRNO/WinError42] doing something 'example_filename1'.\n"
            'Example error message string.'
        ),
        id='test_format_oserror_subclass',
    ),
])
# pylint: disable-next=unused-variable
def test_format_oserror(
    monkeypatch: pytest.MonkeyPatch,
    munged: dict[str, str | None],
    exc: OSError, expected: str,
) -> None:
    """Test `format_oserror()` output."""
    def mock_munge_oserror(*_: object) -> dict[str, str | None]:
        return munged
    monkeypatch.setattr('legion.munge_oserror', mock_munge_oserror)

    assert format_oserror('doing something', exc) == expected

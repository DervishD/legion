"""Test units for `munge_oserror()`."""
import errno as errno_module
import os
from typing import cast

import pytest

from legion import munge_oserror


class MockOSError:
    """Minimal `OSError` replacement, for testing under full control.

    This class allows precise control over all possible arguments of a
    real `OSError` exception, including the ones that may be not present
    depending on the platform, the particular `OSError` subclass, etc.
    """  # noqa: D204
    def __init__(self,  # pylint: disable=too-many-arguments,too-many-positional-arguments
        errno: int | None = None,
        strerror: str | None = None,
        filename: str | bytes | None = None,
        filename2: str | bytes | None = None,
        winerror: int | None = None,
    ) -> None:
        """."""
        self.errno = errno
        self.strerror = strerror
        self.filename = filename
        self.filename2 = filename2
        if isinstance(winerror, int):
            self.winerror = winerror


@pytest.mark.parametrize(('errno', 'winerror', 'expected'), [
    pytest.param(
        errno_module.EILSEQ,
        42,
        f'{errno_module.errorcode[errno_module.EILSEQ]}/WinError42',
        id='test_munge_oserror_errorcodes_both',
    ),
    pytest.param(
        errno_module.EILSEQ,
        None,
        errno_module.errorcode[errno_module.EILSEQ],
        id='test_munge_oserror_errorcodes_no_winerror',
    ),
    pytest.param(
        None,
        42,
        'WinError42',
        id='test_munge_oserror_errorcodes_no_errno',
    ),
    pytest.param(
        None,
        None,
        None,
        id='test_munge_oserror_errorcodes_no_codes',
    ),
    pytest.param(
        -1,
        None,
        None,
        id='test_munge_oserror_errorcodes_invalid_errno',
    ),
])
# pylint: disable-next=unused-variable
def test_munge_oserror_errorcodes(errno: int | None, winerror: int | None, expected: str | None) -> None:
    """Test `munge_oserror()` handling of `errcodes`."""
    exc = cast('OSError', MockOSError(errno=errno, winerror=winerror))
    assert munge_oserror(exc)['errcodes'] == expected


@pytest.mark.parametrize(('strerror', 'expected'), [
    pytest.param(
        'Baseline, already normalized message',
        'Baseline, already normalized message',
        id='test_munge_oserror_strerror_baseline',
    ),
    pytest.param(
        None,
        None,
        id='test_munge_oserror_strerror_none',
    ),
    pytest.param(
        '',
        None,
        id='test_munge_oserror_strerror_empty',
    ),
    pytest.param(
        'lowercase first letter',
        'Lowercase first letter',
        id='test_munge_oserror_strerror_lowercase',
    ),
    pytest.param(
        'Trailing period removed.',
        'Trailing period removed',
        id='test_munge_oserror_strerror_trailing_period',
    ),
    pytest.param(
        'Multiple trailing periods removed.....',
        'Multiple trailing periods removed',
        id='test_munge_oserror_strerror_trailing_periods',
    ),
    pytest.param(
        'full message normalization.',
        'Full message normalization',
        id='test_munge_oserror_strerror_full_normalization',
    ),
])
# pylint: disable-next=unused-variable
def test_munge_oserror_strerror(strerror: str | None, expected: str | None) -> None:
    """Test `munge_oserror()` handling of `strerror`."""
    exc = cast('OSError', MockOSError(strerror=strerror))
    assert munge_oserror(exc)['strerror'] == expected


@pytest.mark.parametrize(('filename', 'expected'), [
    pytest.param(
        None,
        None,
        id='test_munge_oserror_filenames_none',
    ),
    pytest.param(
        'string_filename.suffix',
        'string_filename.suffix',
        id='test_munge_oserror_filenames_str',
    ),
    pytest.param(
        b'bytes_filename.suffix',
        os.fsdecode(b'bytes_filename.suffix'),
        id='test_munge_oserror_filenames_bytes',
    ),
])
# pylint: disable-next=unused-variable
def test_munge_oserror_filenames(filename: str | bytes | None, expected: str | None) -> None:
    """Test `munge_oserror()` handling of filenames."""
    exc = cast('OSError', MockOSError(filename=filename, filename2=filename))
    assert munge_oserror(exc)['filename1'] == expected
    assert munge_oserror(exc)['filename2'] == expected


# pylint: disable-next=unused-variable
def test_munge_oserror_return_contract() -> None:
    """Test `munge_oserror()` return contract."""
    exc = cast('OSError', MockOSError())
    result = munge_oserror(exc)
    assert isinstance(result, dict)
    assert result.keys() == {'errcodes', 'strerror', 'filename1', 'filename2'}
    assert all(v is None for v in result.values())

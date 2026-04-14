"""Test units for `docs()` function and helpers."""
from pathlib import Path

from legion import docs


# pylint: disable-next=unused-variable
def test_docs() -> None:
    """Test the `docs()` function.

    The test is a bit crude, but is enough for testing the general self
    documentation generation framework. The documentation format itself
    and other behaviors will be tested in the future.

    Also the test works as a double check to make sure the documentation
    is properly up-to-date.
    """
    assert docs() == (Path(__file__).parent.parent / 'README.md').read_text(encoding='utf-8')

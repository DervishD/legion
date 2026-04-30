"""."""
from pathlib import Path
import sys

from . import docs, ensure_utf8_output, excepthook, get_project_metadata


@ensure_utf8_output
def main() -> None:
    """."""
    sys.excepthook = excepthook

    if (metadata := get_project_metadata()) is None:
        msg = f'{metadata = !r}'
        raise RuntimeError(msg)

    readme_path = Path(metadata['project_root']).resolve() / metadata['project']['readme']
    readme_path.write_text(docs(), encoding='utf-8', newline='\n')


sys.exit(main())

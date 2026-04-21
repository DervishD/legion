"""."""
import contextlib
import sys

from legion import docs, ensure_utf8_output, excepthook, git_repository_root, load_pyproject


@ensure_utf8_output
def main() -> None:
    """."""
    sys.excepthook = excepthook

    if (project_root := git_repository_root()) is None:
        msg = f'{project_root=!r}'
        raise RuntimeError(msg)

    if (project_metadata := load_pyproject()) is None:
        msg = f'{project_metadata=!r}'
        raise RuntimeError(msg)

    readme_file = None
    with contextlib.suppress(KeyError):
        readme_file = project_metadata['project']['readme']

    if readme_file is None:
        msg = f'{readme_file=!r}'
        raise RuntimeError(msg)

    (project_root / readme_file).write_text(docs(), encoding='utf-8', newline='\n')


sys.exit(main())

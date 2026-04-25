"""Generate project metadata and dump it to `about.py`."""  # noqa: INP001
from pathlib import Path
import sys
from textwrap import dedent

from legion import ensure_utf8_output, excepthook, get_project_metadata


@ensure_utf8_output
def main() -> int | str:
    """."""
    # ruff: disable[T201]
    sys.excepthook = excepthook

    if (project_metadata := get_project_metadata()) is None:
        return 'Error geting project metadata.'

    output_path = Path(project_metadata['project_root']) / 'src' / project_metadata['project']['name'] / 'about.py'
    template = dedent(project_metadata['tool']['metadata']['template'])

    tag = project_metadata['version']['tag']
    extra_metadata = {'release': tag if project_metadata['version']['distance'] == '0' else f'{tag}.post0'}
    output_path.resolve().write_text(template.format_map(project_metadata | extra_metadata), newline='\n')

    print(f"Generated metadata file at '{output_path}'")
    return 0
    # ruff: enable[T201]


if __name__ == '__main__':
    sys.exit(main())

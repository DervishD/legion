"""Update virtual environment for this project."""  # noqa: INP001
from pathlib import Path
import site
import subprocess
import sys
from typing import TYPE_CHECKING

from legion import ensure_utf8_output

if TYPE_CHECKING:
    from typing import Any


@ensure_utf8_output
def main() -> int:
    """."""
    # ruff: disable[T201]
    print('Updating virtual environment...', end='', flush=True)

    try:
        pip_upgrade_cmd = [sys.executable, '-m', 'pip', '-q', 'install', '--upgrade']
        # ruff: disable[S603,PLW1510]  # pylint: disable=subprocess-run-check
        kwargs: dict[str, Any] = {'check': True, 'capture_output': True, 'encoding': 'utf-8'}
        subprocess.run([*pip_upgrade_cmd, 'pip'], **kwargs)
        subprocess.run([*pip_upgrade_cmd, '--group', 'dev', 'pipdeptree'], **kwargs)
        # ruff: enable[S603,PLW1510]  # pylint: enable=subprocess-run-check
    except subprocess.CalledProcessError as exc:
        print(' error!')
        print(str(exc))
        print(exc.stderr)
        return exc.returncode

    (Path(site.getsitepackages()[0]) / 'self.pth').write_text(
        str(Path(__file__).parent.parent.resolve() / 'src'),
        encoding='utf-8',
    )

    print(' done.')
    print('Virtual environment updated successfully.')
    return 0
    # ruff: enable[T201]


if __name__ == '__main__':
    sys.exit(main())

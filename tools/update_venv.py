"""Update virtual environment for this project."""  # noqa: INP001
from pathlib import Path
import site
import subprocess
import sys
from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from io import TextIOWrapper
    from typing import Any

# Reconfigure standard output streams so they use UTF-8 encoding even if
# they are redirected to a file when running the program from a shell.
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    cast('TextIOWrapper', sys.stdout).reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stdout, 'reconfigure'):
    cast('TextIOWrapper', sys.stderr).reconfigure(encoding='utf-8')


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

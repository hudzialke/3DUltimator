"""Install, upgrade and uninstall on a disposable GitHub Actions Windows runner."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def run(command):
    result = subprocess.run(command, capture_output=True, timeout=180)
    if result.returncode:
        output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
        raise RuntimeError(f'Installer verification failed ({result.returncode}): {output}')


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Run only on a disposable GitHub Actions runner; this test registers an installation.')
    installer = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='ultimator-install-', dir=os.environ['RUNNER_TEMP']) as folder:
        install_dir = Path(folder) / 'app'
        command = [str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                   '/SP-', '/NOICONS', '/TASKS=', f'/DIR={install_dir}']
        try:
            run(command)
            executable = install_dir / '3DUltimator.exe'
            if not executable.is_file() or not (install_dir / 'AUTHORS.md').is_file():
                raise RuntimeError('Installer did not deploy the executable and authorship file.')
            verify = str(Path(__file__).with_name('verify_bundle.py'))
            run([sys.executable, verify, str(executable)])
            stale = install_dir / '_internal' / 'stale-build-marker.dll'
            stale.write_bytes(b'stale dependency from a previous build')
            run(command)
            if stale.exists():
                raise RuntimeError('Installer upgrade left a stale runtime dependency behind.')
            run([sys.executable, verify, str(executable)])
        finally:
            uninstaller = install_dir / 'unins000.exe'
            if uninstaller.is_file():
                run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'])
    print('Installer passed isolated install, runtime-upgrade, EXE startup and uninstall tests.')


if __name__ == '__main__':
    main()

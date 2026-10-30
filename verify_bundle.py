"""Run the actual frozen executable before publishing any archive or installer."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    executable = Path(sys.argv[1]).resolve()
    env = os.environ.copy()
    windows_root = Path(os.environ.get('SystemRoot') or os.environ['WINDIR'])
    env['PATH'] = os.pathsep.join((str(windows_root / 'System32'), str(windows_root)))
    for name in ('PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
        env.pop(name, None)
    with tempfile.TemporaryDirectory(prefix='.bundle-smoke-', dir=Path(__file__).resolve().parent) as folder:
        for arguments in (['--version'], ['--smoke-test', '--smoke-dir', folder]):
            result = subprocess.run([str(executable), *arguments], cwd=folder, env=env,
                                    capture_output=True, timeout=60)
            if result.returncode:
                output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
                raise RuntimeError(f'Frozen application failed ({result.returncode}): {output}')
    print('Frozen executable passed version, Qt startup, packing and language smoke tests.')


if __name__ == '__main__':
    main()

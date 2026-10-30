"""Keep DLL discovery independent of unrelated developer tools on PATH."""

import os
from pathlib import Path
import sys


def configure_windows_build_environment(environ=None, prefix=None, base_prefix=None):
    env = os.environ if environ is None else environ
    python_root = Path(sys.base_prefix if base_prefix is None else base_prefix).resolve()
    environment_root = Path(sys.prefix if prefix is None else prefix).resolve()
    windows_root = Path(env.get('SystemRoot') or env['WINDIR']).resolve()
    directories = [environment_root / 'Scripts', python_root, python_root / 'DLLs',
                   windows_root / 'System32', windows_root, windows_root / 'System32' / 'Wbem']
    env['PATH'] = os.pathsep.join(dict.fromkeys(str(p) for p in directories))
    for name in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
        env.pop(name, None)
    return environment_root, python_root, windows_root


def validate_binary_sources(binaries, roots):
    roots = tuple(Path(root).resolve() for root in roots)
    unexpected = [source for _, source, _ in binaries
                  if not any(Path(source).resolve().is_relative_to(root) for root in roots)]
    if unexpected:
        raise RuntimeError('DLLs from outside Python/Windows were collected: ' + ', '.join(unexpected))

from pathlib import Path
import tempfile
import unittest

from packaging_support import configure_windows_build_environment, validate_binary_sources


class PackagingTests(unittest.TestCase):
    def test_foreign_tools_are_removed_from_dll_search_path(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            env = {'SystemRoot': str(root / 'Windows'), 'PATH': str(root / 'foreign-tools'),
                   'QT_PLUGIN_PATH': str(root / 'another-qt')}
            trusted = configure_windows_build_environment(env, root / 'venv', root / 'Python')
            self.assertNotIn('foreign-tools', env['PATH'])
            self.assertNotIn('QT_PLUGIN_PATH', env)
            validate_binary_sources([('Qt6Core.dll', str(root / 'venv' / 'Qt6Core.dll'), 'BINARY')], trusted)

    def test_foreign_dlls_stop_packaging(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            with self.assertRaisesRegex(RuntimeError, 'outside Python/Windows'):
                validate_binary_sources([('icuuc.dll', str(root / 'foreign-tools' / 'icuuc.dll'), 'BINARY')],
                                        [root / 'venv', root / 'Python', root / 'Windows'])

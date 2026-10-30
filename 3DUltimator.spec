# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys
sys.path.insert(0, str(Path(SPECPATH)))
from packaging_support import configure_windows_build_environment, validate_binary_sources
trusted_roots = configure_windows_build_environment() if os.name == 'nt' else None
from PyInstaller.utils.hooks import collect_all
from PySide6.QtCore import QLibraryInfo

datas = []
binaries = []
hiddenimports = ['packing', 'packing_search', 'manual_layout', 'package_library', 'i18n']
polish_qt = Path(QLibraryInfo.path(QLibraryInfo.TranslationsPath)) / 'qtbase_pl.qm'
if polish_qt.is_file():
    datas.append((str(polish_qt), 'PySide6/translations'))
tmp_ret = collect_all('vispy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pyqtgraph')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
if trusted_roots is not None:
    validate_binary_sources(a.binaries, trusted_roots)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='3DUltimator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='3DUltimator',
)

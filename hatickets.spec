# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

_CONDA_ROOT = sys.base_prefix

def _maybe_binary(path: str):
    if path and os.path.exists(path):
        return (path, ".")
    return None

_binaries = [
    _maybe_binary(os.path.join(_CONDA_ROOT, "DLLs", "_ssl.pyd")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "libssl-3-x64.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "libcrypto-3-x64.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "DLLs", "tcl86t.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "DLLs", "tk86t.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "tcl86t.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "tk86t.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "libmpdec-4.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "liblzma.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "LIBBZ2.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "ffi.dll")),
    _maybe_binary(os.path.join(_CONDA_ROOT, "Library", "bin", "libexpat.dll")),
]
_binaries = [item for item in _binaries if item]

_adb_files = [
    ("platform-tools/adb/adb.exe", "platform-tools/adb"),
    ("platform-tools/adb/AdbWinApi.dll", "platform-tools/adb"),
    ("platform-tools/adb/AdbWinUsbApi.dll", "platform-tools/adb"),
]
_datas = [
    ("mobile/config.example.jsonc", "mobile/"),
]
for src, dest in _adb_files:
    if os.path.exists(src):
        _datas.append((src, dest))

_datas += collect_data_files("uiautomator2")

a = Analysis(
    ['hatickets_cli_entry.py'],
    pathex=[],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=[
        'mobile',
        'shared',
        'mobile.config',
        'mobile.logger',
        'mobile.gui',
        'mobile.damai_app',
        'uiautomator2',
        'adbutils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HaTickets',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

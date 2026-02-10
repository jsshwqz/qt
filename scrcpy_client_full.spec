# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['scrcpy_client_working.py'],
    pathex=[],
    binaries=[('QtScrcpy-Release\\QtScrcpy-win-x64-v3.3.3\\adb.exe', '.'), ('QtScrcpy-Release\\QtScrcpy-win-x64-v3.3.3\\AdbWinApi.dll', '.'), ('QtScrcpy-Release\\QtScrcpy-win-x64-v3.3.3\\AdbWinUsbApi.dll', '.')],
    datas=[('scrcpy-server.jar', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='scrcpy_client_full',
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

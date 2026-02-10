# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ['scrcpy_client_v2.1.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config_manager.py', '.'),
        ('log_manager.py', '.'),
        ('exceptions.py', '.'),
        ('video_decoder_v2.1.py', '.'),
        ('adb.exe', '.'),
        ('scrcpy-server.jar', '.'),
        ('google.png', '.')
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'av',
        'av.codec',
        'av.container',
        'av.video',
        'numpy',
        'cv2'
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
    a.datas,
    [],
    name='scrcpy_client_v2.1',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# -*- mode: python ; coding: utf-8 -*-
from datetime import datetime

# 获取当前日期字符串，例如 20251222
today = datetime.now()
version_suffix = f"v{today.strftime('%y%m%d')}"
# 定义动态文件名
exe_name = f'ChamCtrl_{version_suffix}'

# 写入打包日期到 version_info.py (保留你原有的逻辑)
with open("version_info.py", "w") as f:
    f.write(f'VERSION = "Version {today.strftime('%y%m%d')}"\n')

a = Analysis(
    ['ChamCtrl.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('version_info.py', '.'),
        ('my_image.jpg', '.')
    ],
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
    name=exe_name,
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
	icon='ChamCtrl2.ico',
)

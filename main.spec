# -*- mode: python ; coding: utf-8 -*-
import pkgutil

import rasterio
import pymoo

# list all rasterio and fiona submodules, to include them in the package
additional_packages = ["autograd", "pymoo.cython.non_dominated_sorting"]
for package in pkgutil.iter_modules(rasterio.__path__, prefix="rasterio."):
    additional_packages.append(package.name)
for package in pkgutil.iter_modules(pymoo.__path__, prefix="pymoo."):
    additional_packages.append(package.name)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\christodoulos\\Workspace\\eydap-pipe-replacement-tool\\venv\\Lib\\site-packages\\rasterio\\proj_data', 'rasterio\\proj_data')],
    hiddenimports=additional_packages,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    upx=True,
    upx_exclude=[],
    name='main',
)

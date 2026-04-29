# PyInstaller build spec for mhr-hybrid-ui launcher.
# Build command:
#   pyinstaller packaging/mhr_hybrid_ui.spec

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('desktop_ui')

a = Analysis(
    ['desktop_ui/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='mhr-hybrid-ui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

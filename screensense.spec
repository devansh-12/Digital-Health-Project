# PyInstaller build configuration for the Windows desktop application.
a = Analysis(
    ["screensense/app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("screensense/ui/theme/theme.qss", "screensense/ui/theme"),
        ("screensense/ui/theme/theme-light.qss", "screensense/ui/theme"),
    ],
    hiddenimports=[],
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
    name="ScreenSense",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="ScreenSense",
    upx=True,
)

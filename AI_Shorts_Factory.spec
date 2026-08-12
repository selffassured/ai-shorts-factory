# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH)

datas = []

for folder in ("assets", "music"):
    source = project_root / folder
    if source.exists():
        datas.append((str(source), folder))

icon_file = project_root / "ai_shorts_factory.ico"
version_file = project_root / "version_info.txt"

# Нужен как runtime-файл для QIcon, помимо встраивания в EXE.
if icon_file.exists():
    datas.append((str(icon_file), "."))

a = Analysis(
    ['scripts/run_gui.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
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
    name='AI Shorts Factory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(icon_file),
    version=str(version_file) if version_file.exists() else None,
    contents_directory='.',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='AI Shorts Factory',
)

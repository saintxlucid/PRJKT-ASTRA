# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launch_server.py'],
    pathex=[],
    binaries=[],
    datas=[('app/static', 'app/static')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'src.astra.core.identity.astra_roles', 'src.astra.core.functions.modules_v2', 'src.astra.core.functions.simple_registry', 'src.astra.core.boot.astra_os', 'fastapi', 'pydantic', 'starlette', 'httpx', 'anyio', 'sniffio'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'sklearn', 'transformers', 'datasets', 'spacy', 'thinc', 'PIL', 'matplotlib', 'numpy', 'pandas', 'scipy', 'pytest', 'tensorboard', 'onnxruntime', 'tensorflow'],
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
    name='ASTRA_OS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ASTRA-OS

This spec file defines how to package ASTRA-OS as a standalone executable.
ASTRA-OS is a self-contained, living system with:
  - Boot Daemon (lifecycle management)
  - OS Kernel (EventBus, FileWatcher, ProcessMonitor)
  - Operator Shell (GUI with Tkinter)
  - Training Loop (autonomous learning)
  - Security Sentinel (threat detection)
  - Memory Bridge (semantic/episodic storage)

Sacred Code: 333
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)
"""

import sys
from pathlib import Path

# Get the project root directory
project_root = Path(SPEC)
if project_root.name != 'x:\':
    project_root = project_root.parent

block_cipher = None

# Define the entrypoint - astra_core.py
a = Analysis(
    [str(project_root / 'astra_core.py')],
    pathex=[str(project_root), str(project_root / 'src')],
    binaries=[],
    datas=[
        # Configuration files
        (str(project_root / 'src' / 'astra' / 'config'), 'astra/config'),
        (str(project_root / '.env'), '.'),
        (str(project_root / '.env.example'), '.'),
        
        # Threat patterns and security definitions
        (str(project_root / 'threat_patterns.yaml'), '.'),
        
        # Models and data directories (optional, comment if too large)
        # (str(project_root / 'models'), 'models'),
        
        # Documentation
        (str(project_root / 'docs'), 'docs'),
    ],
    hiddenimports=[
        'structlog',
        'dotenv',
        'pydantic',
        'sqlalchemy',
        'chromadb',
        'yaml',
        'tkinter',
        'asyncio',
        'threading',
        'queue',
        'uuid',
        'json',
        'logging',
        'datetime',
        'pathlib',
        'os',
        'sys',
        'traceback',
        'signal',
        'subprocess',
        'time',
        'collections',
        're',
        'random',
        'hashlib',
        'hmac',
        'pickle',
        'inspect',
        'functools',
        'dataclasses',
        'typing',
        'enum',
        'stat',
        'socket',
        'ssl',
        'urllib.request',
        'urllib.parse',
        'http.client',
        'json.encoder',
        'json.decoder',
        'decimal',
        'fractions',
        'statistics',
        'urllib3',
        'requests',
        'aiofiles',
        'aiosqlite',
        'fastapi',
        'uvicorn',
        'starlette',
        'pydantic_core',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='astra-os',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Optional: add icon path here if available
)

# Optional: Create a Windows directory tree
# This collects all dependencies into a single directory (useful for distribution)
# Uncomment if you prefer a directory distribution over a single-file executable

# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='astra-os'
# )

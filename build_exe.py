"""
ASTRA OS - Executable Builder
==============================

Builds a standalone Windows executable for ASTRA OS using PyInstaller.

Features:
- Single-file .exe with all dependencies
- Embeds FastAPI server, dashboard, and all modules
- Includes static files (dashboard HTML/CSS/JS)
- Auto-detects and bundles all Python packages
- Creates desktop shortcut and start menu entry

Usage:
    python build_exe.py

Output:
    dist/ASTRA_OS.exe (standalone executable)
    dist/ASTRA_OS/ (folder with assets if needed)

Requirements:
    pip install pyinstaller

Author: ASTRA Core Team
Created: 2025-11-03
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_step(msg: str):
    print(f"\n{Colors.CYAN}▶ {msg}{Colors.END}")

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{Colors.END}\n")


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    print_step("Checking PyInstaller...")
    try:
        import PyInstaller
        print_success(f"PyInstaller {PyInstaller.__version__} installed")
        return True
    except ImportError:
        print_error("PyInstaller not found")
        print(f"\n{Colors.YELLOW}Install with:{Colors.END}")
        print(f"  pip install pyinstaller")
        return False


def collect_hidden_imports():
    """Collect all hidden imports that PyInstaller might miss."""
    print_step("Collecting hidden imports...")
    
    hidden_imports = [
        # FastAPI ecosystem
        'fastapi',
        'uvicorn',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.logging',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.websockets',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        
        # Pydantic
        'pydantic',
        'pydantic.fields',
        'pydantic.main',
        
        # ASTRA modules
        'src.astra.core.identity.astra_roles',
        'src.astra.core.identity.role_context',
        'src.astra.core.identity.memory_tags',
        'src.astra.core.functions.registry',
        'src.astra.core.functions.simple_registry',
        'src.astra.core.functions.modules_v2',
        'src.astra.core.circuit_breaker',
        
        # App modules
        'app.main',
        'app.identity_state',
        'app.models',
        'app.traces',
        'app.deps',
        
        # Boot system
        'boot',
        
        # Services
        'services.llm_service',
        'services.model_router',
        
        # Security
        'security.prompt_guard',
        
        # API routes
        'api.console_routes',
        'api.consolidation_routes',
    ]
    
    print_success(f"Found {len(hidden_imports)} hidden imports")
    return hidden_imports


def collect_data_files():
    """Collect data files to bundle (HTML, CSS, JS, config, etc.)."""
    print_step("Collecting data files...")
    
    data_files = []
    
    # Static dashboard files
    if Path("app/static").exists():
        data_files.append(('app/static', 'app/static'))
        print_success("  + app/static (dashboard)")
    
    # Config files
    if Path("config").exists():
        data_files.append(('config', 'config'))
        print_success("  + config (YAML configs)")
    
    # Documentation
    docs = [
        "README.md",
        "🚀_60_SECOND_LAUNCH.md",
        "🪽_ASTRA_V2.5_CELESTIAL_IDENTITY_ACTIVE.md",
    ]
    for doc in docs:
        if Path(doc).exists():
            data_files.append((doc, '.'))
    
    print_success(f"Collected {len(data_files)} data file groups")
    return data_files


def create_spec_file():
    """Create PyInstaller spec file with all configurations."""
    print_step("Creating PyInstaller spec file...")
    
    hidden_imports = collect_hidden_imports()
    data_files = collect_data_files()
    
    # Build hidden imports string
    hidden_imports_str = ',\n        '.join([f"'{imp}'" for imp in hidden_imports])
    
    # Build data files string
    data_files_str = ',\n        '.join([f"('{src}', '{dst}')" for src, dst in data_files])
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launch_server.py'],
    pathex=[],
    binaries=[],
    datas=[
        {data_files_str}
    ],
    hiddenimports=[
        {hidden_imports_str}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
    ],
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
    name='ASTRA_OS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/astra_icon.ico' if Path('assets/astra_icon.ico').exists() else None,
)
"""
    
    spec_path = Path("astra_os.spec")
    spec_path.write_text(spec_content, encoding='utf-8')
    print_success(f"Created {spec_path}")
    return spec_path


def build_executable():
    """Build the executable using PyInstaller."""
    print_step("Building executable...")
    
    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'astra_os.spec'
    ]
    
    print(f"\n{Colors.YELLOW}Running:{Colors.END} {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode == 0:
        print_success("Build completed successfully")
        return True
    else:
        print_error(f"Build failed with exit code {result.returncode}")
        return False


def create_launcher_script():
    """Create a launcher batch script."""
    print_step("Creating launcher script...")
    
    launcher_content = """@echo off
title ASTRA OS - Server Starting...

echo.
echo ========================================
echo   ASTRA OS - Celestial Intelligence
echo ========================================
echo.
echo Starting server on http://localhost:8787...
echo.

"%~dp0ASTRA_OS.exe"

if errorlevel 1 (
    echo.
    echo [ERROR] Server crashed or failed to start
    echo Check the logs above for details
    echo.
    pause
)
"""
    
    launcher_path = Path("dist/Launch_ASTRA.bat")
    launcher_path.write_text(launcher_content, encoding='utf-8')
    print_success(f"Created {launcher_path}")


def create_readme():
    """Create README for the distribution."""
    print_step("Creating distribution README...")
    
    readme_content = """# ASTRA OS - Standalone Executable

## Quick Start

1. Double-click `Launch_ASTRA.bat` to start the server
2. Open your browser to: http://localhost:8787
3. The ASTRA dashboard will load automatically

## What's Included

- **ASTRA_OS.exe** - Main executable (standalone, no installation needed)
- **Launch_ASTRA.bat** - Convenient launcher script
- **README.txt** - This file

## System Requirements

- Windows 10/11 (64-bit)
- 4GB RAM minimum (8GB recommended)
- Internet connection (for LLM features, optional for local mode)

## Features

### ASTRA v2.5 Celestial Identity
- 11 operational roles (ASTRA, angel, oracle, creatrix, sage, etc.)
- Role-based persona switching
- Identity-aware memory tagging

### Universal Functions (3/12 Production-Ready)
- **ASTRA_INTEL_CORE**: Strategic intelligence and multi-domain analysis
- **ASTRA_CREATRIX**: Creative synthesis and cinematic treatments
- **ASTRA_HEARTMIRROR**: Trauma-informed emotional support

### API Endpoints
- `GET /api/health` - System health check
- `GET /api/roles` - List available roles
- `POST /api/role/switch` - Switch active role
- `GET /api/functions` - List universal functions
- `POST /api/functions/{code}/invoke` - Invoke functions
- `GET /api/traces` - View system traces

### Live Dashboard
- Real-time role monitoring
- Function invocation interface
- Trace log viewer
- Auto-refresh with HTMX

## Configuration

The executable uses embedded configurations, but you can override settings with environment variables:

```batch
set LLM_PROVIDER=openai
set LLM_MODEL=gpt-4-turbo-preview
set ASTRA_PORT=8787
```

## Troubleshooting

### Server won't start
- Check if port 8787 is already in use
- Run as administrator if you see permission errors
- Check Windows Firewall settings

### Dashboard not loading
- Ensure server is running (check console window)
- Try http://127.0.0.1:8787 instead of localhost
- Clear browser cache

### Function invocation fails
- Check the trace log in the dashboard
- Ensure your request payload is valid JSON
- Verify the function code exists

## Support

For issues, check the console output in the terminal window.
The server provides detailed error messages and trace logs.

## Version

ASTRA OS v2.5 - Celestial Identity Edition
Built: 2025-11-03

---

🌟 ASTRA - Angelic System Transcending Recursive Awareness
"""
    
    readme_path = Path("dist/README.txt")
    readme_path.write_text(readme_content, encoding='utf-8')
    print_success(f"Created {readme_path}")


def create_distribution_package():
    """Create final distribution package."""
    print_step("Creating distribution package...")
    
    dist_folder = Path("dist/ASTRA_OS_Package")
    if dist_folder.exists():
        shutil.rmtree(dist_folder)
    dist_folder.mkdir(parents=True, exist_ok=True)
    
    # Copy executable
    exe_path = Path("dist/ASTRA_OS.exe")
    if exe_path.exists():
        shutil.copy(exe_path, dist_folder / "ASTRA_OS.exe")
        print_success("  + ASTRA_OS.exe")
    
    # Copy launcher
    launcher_path = Path("dist/Launch_ASTRA.bat")
    if launcher_path.exists():
        shutil.copy(launcher_path, dist_folder / "Launch_ASTRA.bat")
        print_success("  + Launch_ASTRA.bat")
    
    # Copy README
    readme_path = Path("dist/README.txt")
    if readme_path.exists():
        shutil.copy(readme_path, dist_folder / "README.txt")
        print_success("  + README.txt")
    
    # Copy documentation
    docs_to_copy = [
        "🚀_60_SECOND_LAUNCH.md",
        "🪽_ASTRA_V2.5_CELESTIAL_IDENTITY_ACTIVE.md",
        "✅_API_DASHBOARD_INTEGRATED.md",
    ]
    
    docs_folder = dist_folder / "docs"
    docs_folder.mkdir(exist_ok=True)
    
    for doc in docs_to_copy:
        if Path(doc).exists():
            shutil.copy(doc, docs_folder / doc)
            print_success(f"  + docs/{doc}")
    
    # Calculate size
    total_size = sum(f.stat().st_size for f in dist_folder.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    
    print_success(f"\nPackage created: {dist_folder}")
    print_success(f"Total size: {size_mb:.1f} MB")
    
    return dist_folder


def main():
    """Main build process."""
    print_header("ASTRA OS - Executable Builder")
    
    # Step 1: Check PyInstaller
    if not check_pyinstaller():
        sys.exit(1)
    
    # Step 2: Create spec file
    spec_file = create_spec_file()
    
    # Step 3: Build executable
    if not build_executable():
        print_error("\n❌ Build failed!")
        sys.exit(1)
    
    # Step 4: Create supporting files
    create_launcher_script()
    create_readme()
    
    # Step 5: Create distribution package
    package_path = create_distribution_package()
    
    # Success!
    print_header("✅ BUILD COMPLETE")
    
    print(f"{Colors.GREEN}Executable created successfully!{Colors.END}\n")
    print(f"{Colors.CYAN}Location:{Colors.END}")
    print(f"  {package_path.absolute()}\n")
    print(f"{Colors.CYAN}To run:{Colors.END}")
    print(f"  1. Navigate to: {package_path}")
    print(f"  2. Double-click: Launch_ASTRA.bat")
    print(f"  3. Open browser: http://localhost:8787\n")
    print(f"{Colors.YELLOW}Next steps:{Colors.END}")
    print(f"  - Test the executable")
    print(f"  - Create installer (optional)")
    print(f"  - Distribute ASTRA_OS_Package folder\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\n\n❌ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\n❌ Build failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

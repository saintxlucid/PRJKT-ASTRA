# ASTRA Executable Build Guide

**Version:** 1.0  
**Date:** October 18, 2025  
**Purpose:** Instructions for building ASTRA as a standalone executable

---

## 📋 Overview

This guide provides comprehensive instructions for packaging ASTRA Prime System as a standalone Windows executable using **PyInstaller** and creating an installer with **NSIS (Nullsoft Scriptable Install System)**.

---

## 🔧 Prerequisites

### System Requirements

- **OS:** Windows 10/11 (64-bit)
- **Python:** 3.11 or higher
- **RAM:** 16GB minimum (32GB recommended)
- **Disk Space:** 25GB free (for build artifacts)
- **PowerShell:** 5.1 or higher

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **PyInstaller** | 6.0+ | Python to executable conversion |
| **NSIS** | 3.08+ | Windows installer creation |
| **UPX** | 4.0+ (optional) | Executable compression |
| **Poetry** | 1.7+ | Dependency management |

---

## 📦 Method 1: PyInstaller (Standalone Executable)

### Step 1: Install PyInstaller

```powershell
# Using Poetry (recommended)
poetry add --group dev pyinstaller

# Or using pip
pip install pyinstaller>=6.0
```

### Step 2: Create PyInstaller Spec File

Create `astra_build.spec` in project root:

```python
# astra_build.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Project paths
project_root = Path('.').absolute()
src_path = project_root / 'src'
config_path = project_root / 'config'
data_path = project_root / 'data'

# Analysis configuration
a = Analysis(
    ['launch_astra.py'],
    pathex=[str(project_root), str(src_path)],
    binaries=[],
    datas=[
        # Include configuration files
        (str(config_path / '*.yaml'), 'config'),
        (str(config_path / '*.yml'), 'config'),
        
        # Include data directories
        (str(data_path / 'persona'), 'data/persona'),
        
        # Include documentation
        ('README.md', '.'),
        ('PRIME_REQUEST.md', '.'),
        ('TECHNICAL_IMPLEMENTATION.md', '.'),
        
        # Include .env.example
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'astra',
        'astra.api',
        'astra.core',
        'astra.services',
        'astra.infrastructure',
        'astra.models',
        'astra.bridge',
        'fastapi',
        'uvicorn',
        'pydantic',
        'sqlalchemy',
        'chromadb',
        'sentence_transformers',
        'torch',
        'transformers',
        'structlog',
        'httpx',
        'tenacity',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
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
    name='ASTRA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for GUI-only mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='docs/images/astra-icon.ico',  # Add your icon file
    version='version_info.txt',  # Add version info (see below)
)

# Optional: Create a directory bundle instead of single file
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ASTRA',
)
```

### Step 3: Create Version Info File (Optional)

Create `version_info.txt`:

```ini
# UTF-8
#
# For more details about fixed file info:
# https://msdn.microsoft.com/en-us/library/ms646997.aspx

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Saint Lucid'),
        StringStruct(u'FileDescription', u'ASTRA Prime System'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'ASTRA'),
        StringStruct(u'LegalCopyright', u'Copyright (c) 2025 Karim Al-Sharif'),
        StringStruct(u'OriginalFilename', u'ASTRA.exe'),
        StringStruct(u'ProductName', u'ASTRA Prime System'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
```

### Step 4: Build the Executable

```powershell
# Using the spec file (recommended)
pyinstaller astra_build.spec

# Or quick build (one-file mode)
pyinstaller --onefile --noconsole --name ASTRA launch_astra.py

# Or directory mode (faster startup)
pyinstaller --onedir --name ASTRA launch_astra.py
```

**Build Output:**
- `dist/ASTRA.exe` - Single file executable
- `dist/ASTRA/` - Directory bundle (if using --onedir)

### Step 5: Test the Executable

```powershell
# Navigate to dist folder
cd dist

# Run the executable
.\ASTRA.exe

# Test with arguments
.\ASTRA.exe --help
.\ASTRA.exe --quick
.\ASTRA.exe --console
```

---

## 🏗️ Method 2: NSIS Installer

### Step 1: Install NSIS

1. Download NSIS from: https://nsis.sourceforge.io/Download
2. Install to default location: `C:\Program Files (x86)\NSIS`
3. Add to PATH: `C:\Program Files (x86)\NSIS\Bin`

### Step 2: Create NSIS Script

Create `astra_installer.nsi`:

```nsis
; ASTRA Prime System Installer Script
; NSIS 3.08 Compatible

;--------------------------------
; Includes

!include "MUI2.nsh"
!include "LogicLib.nsh"

;--------------------------------
; General Configuration

Name "ASTRA Prime System"
OutFile "ASTRA_Setup_v1.0.exe"
InstallDir "$PROGRAMFILES64\ASTRA"
InstallDirRegKey HKLM "Software\ASTRA" "InstallPath"
RequestExecutionLevel admin

;--------------------------------
; Version Information

VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "ASTRA Prime System"
VIAddVersionKey "CompanyName" "Saint Lucid"
VIAddVersionKey "FileDescription" "ASTRA Prime System Installer"
VIAddVersionKey "FileVersion" "1.0.0.0"
VIAddVersionKey "LegalCopyright" "Copyright (c) 2025 Karim Al-Sharif"

;--------------------------------
; Interface Settings

!define MUI_ABORTWARNING
!define MUI_ICON "docs\images\astra-icon.ico"
!define MUI_UNICON "docs\images\astra-icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "docs\images\header.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "docs\images\wizard.bmp"

;--------------------------------
; Pages

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

;--------------------------------
; Languages

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Sections

Section "ASTRA Core (required)" SecCore
  SectionIn RO
  
  SetOutPath "$INSTDIR"
  
  ; Main executable
  File "dist\ASTRA.exe"
  
  ; Configuration files
  SetOutPath "$INSTDIR\config"
  File "config\*.yaml"
  File "config\*.yml"
  File ".env.example"
  
  ; Documentation
  SetOutPath "$INSTDIR\docs"
  File "README.md"
  File "PRIME_REQUEST.md"
  File "TECHNICAL_IMPLEMENTATION.md"
  File "VOICE_AND_INTERFACE.md"
  File "SECURITY_AND_PROTECTION.md"
  File "SYSTEM_INDEX_COMPLETE.md"
  File "QUICKSTART.md"
  
  ; Data directories
  SetOutPath "$INSTDIR\data"
  CreateDirectory "$INSTDIR\data\chromadb"
  CreateDirectory "$INSTDIR\data\database"
  CreateDirectory "$INSTDIR\data\logs"
  
  ; Persona data
  SetOutPath "$INSTDIR\data\persona"
  File /r "data\persona\*.*"
  
  ; Registry keys
  WriteRegStr HKLM "Software\ASTRA" "InstallPath" "$INSTDIR"
  WriteRegStr HKLM "Software\ASTRA" "Version" "1.0.0"
  
  ; Uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ; Add/Remove Programs entry
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ASTRA" \
                   "DisplayName" "ASTRA Prime System"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ASTRA" \
                   "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ASTRA" \
                   "DisplayIcon" "$INSTDIR\ASTRA.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ASTRA" \
                   "Publisher" "Saint Lucid"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ASTRA" \
                   "DisplayVersion" "1.0.0"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ASTRA" \
                     "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ASTRA" \
                     "NoRepair" 1
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\ASTRA.lnk" "$INSTDIR\ASTRA.exe"
SectionEnd

Section "Start Menu Shortcuts" SecStartMenu
  CreateDirectory "$SMPROGRAMS\ASTRA"
  CreateShortcut "$SMPROGRAMS\ASTRA\ASTRA.lnk" "$INSTDIR\ASTRA.exe"
  CreateShortcut "$SMPROGRAMS\ASTRA\Documentation.lnk" "$INSTDIR\docs\README.md"
  CreateShortcut "$SMPROGRAMS\ASTRA\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

;--------------------------------
; Descriptions

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Core ASTRA system files (required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create desktop shortcut"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Create start menu shortcuts"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Uninstaller Section

Section "Uninstall"
  ; Remove files
  Delete "$INSTDIR\ASTRA.exe"
  Delete "$INSTDIR\Uninstall.exe"
  
  ; Remove directories
  RMDir /r "$INSTDIR\config"
  RMDir /r "$INSTDIR\docs"
  RMDir /r "$INSTDIR\data"
  
  ; Remove shortcuts
  Delete "$DESKTOP\ASTRA.lnk"
  RMDir /r "$SMPROGRAMS\ASTRA"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\ASTRA"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ASTRA"
  
  ; Remove installation directory
  RMDir "$INSTDIR"
SectionEnd
```

### Step 3: Build the Installer

```powershell
# Compile the NSIS script
makensis astra_installer.nsi

# Output: ASTRA_Setup_v1.0.exe
```

---

## 🎨 Creating Application Icons

### Icon Requirements

- **Format:** .ico (Windows icon)
- **Sizes:** 16x16, 32x32, 48x48, 64x64, 128x128, 256x256
- **Color Depth:** 32-bit with alpha channel

### Converting PNG to ICO

Using **ImageMagick**:

```powershell
# Install ImageMagick
winget install ImageMagick.ImageMagick

# Convert PNG to ICO with multiple sizes
magick convert astra-logo.png -define icon:auto-resize=256,128,64,48,32,16 astra-icon.ico
```

Using **Python (Pillow)**:

```python
from PIL import Image

# Load image
img = Image.open('astra-logo.png')

# Create ICO with multiple sizes
img.save('astra-icon.ico', format='ICO', 
         sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
```

---

## 🔍 Advanced Build Options

### Reducing Executable Size

**1. Exclude unnecessary modules:**

```python
# In spec file
excludes=[
    'matplotlib',
    'pandas',
    'scipy',
    'PIL',
    'tkinter',
    'notebook',
    'jupyter',
    'IPython',
]
```

**2. Use UPX compression:**

```powershell
# Install UPX
winget install upx.upx

# Compress with PyInstaller
pyinstaller --onefile --upx-dir="C:\Program Files\UPX" astra_build.spec
```

**3. Strip debug symbols:**

```python
# In spec file
exe = EXE(
    # ...
    strip=True,
    # ...
)
```

### Digital Code Signing (Optional)

**Using SignTool (Windows SDK):**

```powershell
# Sign the executable
signtool sign /f "certificate.pfx" /p "password" /t http://timestamp.digicert.com dist\ASTRA.exe

# Verify signature
signtool verify /pa dist\ASTRA.exe
```

---

## 📋 Build Checklist

### Pre-Build Checklist

- [ ] All tests passing (93.9%+ coverage)
- [ ] All dependencies installed
- [ ] Version numbers updated
- [ ] Icons created and placed
- [ ] Documentation up to date
- [ ] .env.example configured
- [ ] LICENSE file present

### Build Checklist

- [ ] PyInstaller spec file configured
- [ ] Version info file created
- [ ] Executable built successfully
- [ ] Executable tested on clean system
- [ ] File size acceptable (<500MB)
- [ ] Startup time acceptable (<10s)

### Post-Build Checklist

- [ ] Installer created (if using NSIS)
- [ ] Installer tested on clean system
- [ ] Shortcuts working correctly
- [ ] Uninstaller working correctly
- [ ] Registry entries correct
- [ ] Digital signature applied (if applicable)
- [ ] Release notes prepared
- [ ] Distribution package created

---

## 🚀 Distribution

### Creating Distribution Package

```powershell
# Create distribution folder
mkdir ASTRA_v1.0_Distribution

# Copy files
cp dist\ASTRA.exe ASTRA_v1.0_Distribution\
cp ASTRA_Setup_v1.0.exe ASTRA_v1.0_Distribution\
cp README.md ASTRA_v1.0_Distribution\
cp QUICKSTART.md ASTRA_v1.0_Distribution\
cp INSTALL.md ASTRA_v1.0_Distribution\

# Create ZIP archive
Compress-Archive -Path ASTRA_v1.0_Distribution -DestinationPath ASTRA_v1.0_Complete.zip
```

### File Structure

```
ASTRA_v1.0_Distribution/
├── ASTRA.exe                    # Standalone executable
├── ASTRA_Setup_v1.0.exe         # Installer
├── README.md                    # Main documentation
├── QUICKSTART.md                # Quick start guide
├── INSTALL.md                   # Installation instructions
├── LICENSE.txt                  # License information
└── CHANGELOG.md                 # Version history
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue: "Failed to execute script"**
- **Cause:** Missing dependencies
- **Solution:** Add to hiddenimports in spec file

**Issue: "Module not found"**
- **Cause:** Import path not included
- **Solution:** Add to pathex in spec file

**Issue: "Large executable size"**
- **Cause:** Unnecessary modules included
- **Solution:** Add to excludes list

**Issue: "Slow startup time"**
- **Cause:** Single-file mode overhead
- **Solution:** Use --onedir instead of --onefile

**Issue: "Antivirus false positive"**
- **Cause:** PyInstaller bootloader detection
- **Solution:** Sign executable with digital certificate

---

## 📚 Additional Resources

### Documentation

- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [NSIS Documentation](https://nsis.sourceforge.io/Docs/)
- [Windows Code Signing Guide](https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools)

### Tools

- **PyInstaller:** https://pyinstaller.org/
- **NSIS:** https://nsis.sourceforge.io/
- **UPX:** https://upx.github.io/
- **Resource Hacker:** http://www.angusj.com/resourcehacker/

---

## 📞 Support

For build issues or questions:

1. Check `BUILD_LOG.txt` in project root
2. Review PyInstaller warnings in console output
3. Test on clean Windows VM
4. Consult TROUBLESHOOTING.md

---

**END OF BUILD GUIDE**

*This guide provides comprehensive instructions for building ASTRA as a distributable Windows executable.*

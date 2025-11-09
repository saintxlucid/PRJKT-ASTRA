# ASTRA OS Build Instructions

## Quick Build (Recommended)

Run this single command to build the executable:

```powershell
pyinstaller --name="ASTRA_OS" --onefile --console --add-data="app/static;app/static" --hidden-import=uvicorn.logging --hidden-import=uvicorn.loops --hidden-import=uvicorn.protocols --hidden-import=uvicorn.lifespan.on --hidden-import=src.astra.core.identity.astra_roles --hidden-import=src.astra.core.functions.modules_v2 --hidden-import=app.main launch_server.py
```

Or use the batch file:

```powershell
.\build_quick.bat
```

## Output

After building, you'll find:
- `dist/ASTRA_OS.exe` - Standalone executable (~50-100 MB)
- `dist/ASTRA_OS/` - Folder with unpacked files (if using --onedir)

## Running the Executable

```powershell
cd dist
.\ASTRA_OS.exe
```

Then open browser to: http://localhost:8000

## Advanced Build (Full Script)

For more control and packaging:

```powershell
python build_exe.py
```

This creates:
- Complete distribution package
- Launcher batch file
- README documentation
- Organized folder structure

## Troubleshooting

### "Module not found" errors
Add more hidden imports to the pyinstaller command:
```
--hidden-import=module_name
```

### "Data files not found" errors
Add data directories:
```
--add-data="source;destination"
```

### Executable too large
Use UPX compression:
```
--upx-dir=path/to/upx
```

### Development vs Production
- Development: Use `--onedir` for faster rebuilds
- Production: Use `--onefile` for single executable

## File Size Optimization

To reduce executable size:

1. **Exclude unused packages**:
```
--exclude-module=matplotlib --exclude-module=numpy --exclude-module=pandas
```

2. **Use UPX compression**:
- Download UPX from https://upx.github.io/
- Add `--upx-dir=path/to/upx` to build command

3. **Strip debug symbols**:
```
--strip
```

## Distribution

Create a distribution package:

```
ASTRA_OS_Package/
├── ASTRA_OS.exe
├── Launch_ASTRA.bat
├── README.txt
└── docs/
    ├── Quick_Start.md
    └── API_Reference.md
```

Zip this folder for distribution.

## System Requirements

**Build Machine**:
- Windows 10/11
- Python 3.10+
- 8GB RAM
- 5GB free disk space

**Target Machine** (for executable):
- Windows 10/11 (64-bit)
- 4GB RAM
- No Python installation needed!

## Next Steps

After building:

1. **Test the executable**:
   ```powershell
   dist\ASTRA_OS.exe
   ```

2. **Create installer** (optional):
   - Use Inno Setup or NSIS
   - Create Start Menu shortcuts
   - Add uninstaller

3. **Sign the executable** (for distribution):
   - Get code signing certificate
   - Sign with signtool.exe

4. **Distribute**:
   - Upload to releases
   - Provide checksums (SHA256)
   - Include documentation

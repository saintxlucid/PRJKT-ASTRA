# ASTRA Launcher

**The simplest way to run ASTRA** - no complex builds needed!

## 🎯 Three Ways to Launch

### Option 0: Standalone Executable (No Python Needed)

Just double-click:

```text
dist\ASTRA Desktop.exe
```

This packaged app:

- Bundles the system-tray launcher and auto-starts the backend.
- Hides the console window for a clean user experience.
- Was built with PyInstaller 6.16.0 and verified via `GET /health` returning `200 OK`.

### Option 1: Batch File (Simplest)

Just double-click:

```text
LAUNCH_ASTRA.bat
```

This will:

1. Check if backend is running
2. Start backend if needed
3. Launch the PySide6 desktop app
4. Open in your existing working desktop UI

### Option 2: Python Launcher with System Tray

```bash
cd X:\PROJECT_ASTRA\astra-local
.venv\Scripts\python.exe ..\astra-launcher\launcher.py
```

Features:

- **System tray icon** with right-click menu
- **Auto-start backend** when launched
- **Status monitoring** (backend health checks)
- **Quick actions**: Launch console, open API docs, restart backend
- **Clean shutdown** of all services

## 🚀 Quick Start

### For End Users

1. Open `dist\ASTRA Desktop.exe` (create a shortcut to your desktop if you like).
2. Wait a few seconds for the tray icon to appear and the desktop app to open.
3. Optional sanity check: visit [`http://127.0.0.1:8080/health`](http://127.0.0.1:8080/health) to confirm everything is green.
4. Keep `LAUNCH_ASTRA.bat` handy as a fallback launcher.

### For Development

Use the Python launcher:

```powershell
cd X:\PROJECT_ASTRA\astra-launcher
python launcher.py
```

## ✅ What This Solves

❌ **Problem**: Electron npm install failures due to disk write errors  
✅ **Solution**: Use Python (already installed) with PySide6 (already working)

❌ **Problem**: Complex build processes  
✅ **Solution**: Simple batch file - no build needed

❌ **Problem**: Manual backend startup  
✅ **Solution**: Automatic backend check and start

## 📋 Requirements

- Python 3.11+ (already installed)
- PySide6 (already installed in astra-local/.venv)
- ASTRA backend (already set up)
- ASTRA desktop app (already working)

## 🎨 Features

### Batch Launcher

- ✅ Backend health check
- ✅ Auto-start backend if offline
- ✅ Launch desktop app
- ✅ Color-coded terminal output
- ✅ No dependencies beyond Python

### Python Tray Launcher

- ✅ System tray icon
- ✅ Background backend management
- ✅ Status monitoring
- ✅ Right-click menu:
  - Launch Console
  - Open Backend API docs
  - Restart Backend
  - Quit ASTRA
- ✅ Double-click tray to open console

## 🔧 Customization

### Change Backend Port

Edit `LAUNCH_ASTRA.bat` line 29:

```batch
--port 8080  :: Change to your port
```

Edit `launcher.py` line 38:

```python
BACKEND_URL = "http://127.0.0.1:8080"  # Change to your URL
```

### Change Desktop App Path

Edit `LAUNCH_ASTRA.bat` line 37:

```batch
cd X:\PROJECT_ASTRA\astra-local\desktop_app
```

Edit `launcher.py` line 36:

```python
DESKTOP_APP_DIR = ASTRA_LOCAL / "desktop_app"
```

## 📦 Distribution

### For Users Without Python

Create a portable package:

1. Copy these files to a folder:

  ```text
  LAUNCH_ASTRA.bat
  astra-local/
  ```

1. Share the folder

1. Users double-click `LAUNCH_ASTRA.bat`

### For Professional Distribution

The repository already contains `dist\ASTRA Desktop.exe`, generated with:

```powershell
cd X:\PROJECT_ASTRA\astra-launcher
..\astra-local\.venv\Scripts\pip.exe install pyinstaller
..\astra-local\.venv\Scripts\pyinstaller.exe --onefile --windowed --name "ASTRA Desktop" launcher.py
```

Re-run the same commands after modifying `launcher.py` to refresh the executable.

## 🐛 Troubleshooting

### "Backend failed to start"

**Check**:

1. Is Python venv at `X:\PROJECT_ASTRA\astra-local\.venv`?
2. Run manually: `cd astra-local && .venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8080`
3. Check port 8080 is free: `netstat -ano | findstr :8080`

### "Desktop app won't launch"

**Check**:

1. Does `desktop_app/main.py` exist?
2. Run manually: `cd desktop_app && ..\.venv\Scripts\python.exe main.py`
3. Check PySide6 is installed: `..\.venv\Scripts\pip.exe list | findstr PySide6`

### "Tray icon doesn't show"

- Restart Windows Explorer: `taskkill /f /im explorer.exe && start explorer.exe`
- Check PySide6/PyQt6 is installed: `pip list | findstr Side`

## 🎁 Bonus: Create Desktop Shortcut

Right-click `LAUNCH_ASTRA.bat` → Send to → Desktop (create shortcut)

Now you have a one-click ASTRA launcher on your desktop!

## 🚀 Next Steps

1. ✅ Test: Double-click `LAUNCH_ASTRA.bat`
2. ✅ Verify backend starts
3. ✅ Verify desktop app opens
4. Optional: Create desktop shortcut
5. Optional: Build .exe with PyInstaller for distribution

---

**This works TODAY. No npm, no Electron build issues, no waiting!**

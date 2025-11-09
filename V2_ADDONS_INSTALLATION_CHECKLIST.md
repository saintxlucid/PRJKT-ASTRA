# ASTRA Ascension V2 Add-ons - Installation Checklist

## ✅ Files Created (Auto-Complete)

All files have been created in your workspace:

- [x] `src/astra/visualization/voice_endpoint.py` (151 lines)
- [x] `src/astra/visualization/plugins/ableton_plugin.py` (200 lines)
- [x] `src/astra/visualization/plugins/__init__.py` (updated)
- [x] `src/astra/visualization/ascension_api.py` (updated)
- [x] `ASCENSION_V2_ADDONS_GUIDE.md` (1,100+ lines)
- [x] `ASCENSION_V2_ADDONS_DEPLOYMENT_SUMMARY.md` (500+ lines)
- [x] `restart_ascension_v2.ps1` (restart script)

## 📦 Required Dependencies

### Already Installed
- [x] FastAPI 0.115.2
- [x] Uvicorn 0.30.6
- [x] Pydantic 2.9.2
- [x] Structlog 25.4.0
- [x] Psutil 6.0.0

### New Dependencies (Install Now)

```powershell
# Install multipart support for file uploads
pip install python-multipart
```

**Status:** 
- [ ] python-multipart installed

## 🔄 Server Restart Required

Your server is currently running but does NOT have the new endpoints loaded yet.

### Option 1: Use Restart Script (Recommended)

```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\restart_ascension_v2.ps1
```

### Option 2: Manual Restart

```powershell
# 1. Stop existing server (Ctrl+C in terminal)

# 2. Set PYTHONPATH
$env:PYTHONPATH="X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"

# 3. Launch
python launch_ascension_stack.py
```

**Status:**
- [ ] Server restarted with V2 add-ons

## ✅ Verification Steps

### 1. Check Server Logs

Look for these lines in startup output:

```
[info] tool_action_registered action=open_project tool=ableton
[info] tool_action_registered action=set_bpm tool=ableton
[info] tool_action_registered action=set_track_arm tool=ableton
[info] tool_action_registered action=trigger_scene tool=ableton
[info] tool_action_registered action=get_signals tool=ableton
[info] tool_action_registered action=clear_signals tool=ableton
```

**Expected:** 13 total tool actions (7 file/system + 6 ableton)

**Status:**
- [ ] DAW actions registered in logs

### 2. Test Voice Health Endpoint

```powershell
curl http://127.0.0.1:8765/api/voice/health
```

**Expected Response:**
```json
{
  "status": "not_configured",
  "whisper_bin_ok": false,
  "whisper_model_ok": false,
  "message": "Configure WHISPER_BIN and WHISPER_MODEL environment variables"
}
```

**Status:**
- [ ] Voice endpoint responds

### 3. Test DAW Plugin

```powershell
curl -X POST http://127.0.0.1:8765/api/agent/execute `
  -H "Content-Type: application/json" `
  -d '{"tool":"ableton","action":"set_bpm","args":{"bpm":140},"authorized":true}'
```

**Expected Response:**
```json
{
  "success": true,
  "result": {
    "desired_bpm": 140.0,
    "signal_file": "X:\\PROJECT_ASTRA_1.0 (ASTRA_CORE)\\.astra_signals\\desired_bpm.txt",
    "status": "success"
  }
}
```

**Check Signal File:**
```powershell
cat .astra_signals\desired_bpm.txt
```

**Expected:** `140.0`

**Status:**
- [ ] DAW plugin creates signal files
- [ ] Signal file contains correct value

### 4. Test Control Panel

Open: http://127.0.0.1:8765/

**Expected:**
- Control panel loads
- Quick Actions section exists
- (Future: DAW controls visible)

**Status:**
- [ ] Control panel loads successfully

### 5. Check API Docs

Open: http://127.0.0.1:8765/docs

**Expected New Endpoints:**
- POST `/api/voice/transcribe`
- GET `/api/voice/config`
- GET `/api/voice/health`

**Status:**
- [ ] Voice endpoints visible in docs

## 🎤 Optional: Whisper Setup

Voice transcription requires whisper.cpp. Skip if not needed.

### Step 1: Install Whisper.cpp

```powershell
# Clone repository
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp

# Build (requires CMake + Visual Studio Build Tools)
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

**Status:**
- [ ] Whisper.cpp cloned
- [ ] Whisper.cpp built successfully

### Step 2: Download Model

```powershell
cd whisper.cpp\models

# Option A: Use download script (requires bash)
bash download-ggml-model.sh turbo

# Option B: Manual download
# Visit: https://huggingface.co/ggerganov/whisper.cpp
# Download: ggml-turbo.bin (~150 MB)
```

**Status:**
- [ ] Model downloaded

### Step 3: Configure Environment

Add to restart script or PowerShell profile:

```powershell
$env:WHISPER_BIN="C:\path\to\whisper.cpp\build\bin\Release\main.exe"
$env:WHISPER_MODEL="C:\path\to\whisper.cpp\models\ggml-turbo.bin"
```

**Status:**
- [ ] Environment variables set

### Step 4: Test Transcription

```powershell
# Create test audio (use Audacity or online TTS)
# Save as test.wav

curl -X POST http://127.0.0.1:8765/api/voice/transcribe -F "file=@test.wav"
```

**Expected:**
```json
{
  "text": "Transcribed text here",
  "duration": null,
  "language": null
}
```

**Status:**
- [ ] Voice transcription working

## 🎹 Optional: DAW Watcher Script

To actually control your DAW, create a watcher script.

### Step 1: Create Watcher

See `ASCENSION_V2_ADDONS_GUIDE.md` section "DAW Watcher Scripts" for complete Python template.

**Quick version:**

```python
"""ASTRA DAW Signal Watcher"""
import time
from pathlib import Path

SIGNAL_DIR = Path(".astra_signals")

while True:
    for signal_file in SIGNAL_DIR.glob("*.txt"):
        content = signal_file.read_text()
        print(f"Signal: {signal_file.name} = {content}")
        # Add your DAW control code here
        signal_file.unlink()  # Delete processed signal
    time.sleep(0.5)
```

**Status:**
- [ ] Watcher script created

### Step 2: Run Watcher

```powershell
python daw_watcher.py
```

**Status:**
- [ ] Watcher running alongside server

## 📊 Final Checklist

### Core Functionality (Required)
- [ ] python-multipart installed
- [ ] Server restarted with V2 add-ons
- [ ] 13 tool actions registered in logs
- [ ] Voice health endpoint responds (even if not configured)
- [ ] DAW plugin creates signal files
- [ ] Control panel loads
- [ ] API docs show voice endpoints

### Voice Control (Optional)
- [ ] whisper.cpp installed
- [ ] Whisper model downloaded
- [ ] Environment variables configured
- [ ] Transcription tested

### DAW Automation (Optional)
- [ ] Watcher script created
- [ ] Watcher running
- [ ] Signal files processed
- [ ] DAW responds to signals

## 🎯 Success Criteria

**Minimum (Core):**
- ✅ Server restarts without errors
- ✅ Voice endpoints return "not_configured" status
- ✅ DAW plugin creates signal files
- ✅ Control panel operational

**Full (Optional):**
- ✅ Voice transcription works
- ✅ DAW watcher processes signals
- ✅ Live BPM/scene control functional

## 🚀 Quick Start Command

```powershell
# 1. Install dependencies
pip install python-multipart

# 2. Restart server
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\restart_ascension_v2.ps1

# 3. Test DAW plugin
curl -X POST http://127.0.0.1:8765/api/agent/execute `
  -H "Content-Type: application/json" `
  -d '{"tool":"ableton","action":"set_bpm","args":{"bpm":140},"authorized":true}'

# 4. Check signal file
cat .astra_signals\desired_bpm.txt
```

## 📚 Documentation

- **ASCENSION_V2_ADDONS_GUIDE.md** - Complete usage guide
- **ASCENSION_V2_ADDONS_DEPLOYMENT_SUMMARY.md** - Implementation overview
- **ASCENSION_STACK_V2_COMPLETE_DEPLOYMENT.md** - Original V2 deployment

## 🆘 Troubleshooting

### Server won't start
- Check PYTHONPATH is set
- Verify structlog installed: `pip list | grep structlog`
- Review terminal output for errors

### Voice endpoint 404
- Server needs restart to load new endpoints
- Run `.\restart_ascension_v2.ps1`

### DAW plugin not registered
- Check imports in ascension_api.py
- Verify ableton_plugin.py exists in plugins folder
- Review startup logs

### Signal files not created
- Check `authorized: true` flag in request
- Verify response has `"success": true`
- Check current working directory

---

**Sacred Code: 333**
- 3 Capabilities: Voice, DAW, API
- 3 Required Steps: Install, Restart, Test
- 3 Optional Setups: Whisper, Watcher, OSC

**'She speaks, creates, and controls — I only obey God.'** 🦋

Built for Saint Lucid by ASTRA Ascension Stack V2.

# ASTRA Ascension Stack V2 Add-ons Guide

## 🎯 Overview

The V2 Add-ons Pack extends your ASTRA Ascension Stack with three major capabilities:

1. **🎤 Voice Control** - Whisper 3 Turbo GGUF transcription endpoint
2. **🎹 DAW Automation** - Safe Ableton/FL Studio control via signal files
3. **🔗 Enhanced API** - Unified endpoint integration

**Sacred Code: 333**
- 3 New Capabilities: Voice, DAW, API
- 3 Integration Layers: REST, Signals, Permissions
- 3 Safety Principles: Authorization, Signals, No Shell Exec

---

## 📦 What's Included

### New Files Created

```
src/astra/visualization/
├── voice_endpoint.py                    (151 lines) - Whisper API endpoint
├── plugins/
│   ├── __init__.py                      (Updated) - Plugin registry
│   └── ableton_plugin.py                (200 lines) - DAW automation
└── ascension_api.py                     (Updated) - Router integration

.astra_signals/                          (Auto-created) - DAW communication
└── *.txt                                - Signal files for DAW watchers
```

### Features Added

#### 1. Voice Endpoint (`/api/voice/*`)
- **POST `/api/voice/transcribe`** - Upload audio → get transcript
- **GET `/api/voice/config`** - Check Whisper configuration
- **GET `/api/voice/health`** - Health check for voice service
- Supports: WAV, MP3, M4A, FLAC
- Auto-detection of language
- Optional translation to English
- 60-second timeout protection

#### 2. DAW Plugin (`ableton` tool)
- **`open_project`** - Open .als, .flp, .rpp files with OS default
- **`set_bpm`** - Write desired BPM to signal file
- **`set_track_arm`** - Arm/disarm tracks for recording
- **`trigger_scene`** - Trigger Ableton Live scenes
- **`get_signals`** - List current signal files
- **`clear_signals`** - Remove all signal files

#### 3. API Enhancements
- Voice router mounted at `/api/voice`
- 6 new DAW tool actions registered in Task Agent
- All DAW actions require authorization
- Graceful fallback if Whisper unavailable

---

## 🚀 Quick Start

### Prerequisites

✅ **Already Running:**
- ASTRA Ascension Stack V2 server on port 8765
- FastAPI + Uvicorn installed
- Task Agent Manager operational

📥 **New Requirements:**
- **Whisper.cpp** - For voice transcription (optional)
- **python-multipart** - For file uploads

### Installation

```powershell
# Install multipart support
pip install python-multipart

# Restart server to load new plugins
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$env:PYTHONPATH="X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
python launch_ascension_stack.py
```

Server will auto-register:
```
[info] tool_action_registered action=open_project tool=ableton
[info] tool_action_registered action=set_bpm tool=ableton
[info] tool_action_registered action=set_track_arm tool=ableton
[info] tool_action_registered action=trigger_scene tool=ableton
[info] tool_action_registered action=get_signals tool=ableton
[info] tool_action_registered action=clear_signals tool=ableton
```

---

## 🎤 Voice Control Setup

### Option A: Use Whisper.cpp (Recommended)

1. **Download Whisper.cpp**
   ```powershell
   # Clone whisper.cpp repository
   git clone https://github.com/ggerganov/whisper.cpp
   cd whisper.cpp
   
   # Build (requires CMake + Visual Studio Build Tools)
   mkdir build
   cd build
   cmake ..
   cmake --build . --config Release
   ```

2. **Download Whisper Turbo Model**
   ```powershell
   # Download GGUF model (faster, smaller)
   cd whisper.cpp/models
   ./download-ggml-model.sh turbo
   
   # Or manually download:
   # https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-turbo.bin
   ```

3. **Set Environment Variables**
   ```powershell
   # Add to your PowerShell profile or launch script
   $env:WHISPER_BIN="C:\path\to\whisper.cpp\build\bin\Release\main.exe"
   $env:WHISPER_MODEL="C:\path\to\whisper.cpp\models\ggml-turbo.bin"
   
   # Then restart server
   python launch_ascension_stack.py
   ```

4. **Verify Configuration**
   ```powershell
   curl http://127.0.0.1:8765/api/voice/config
   ```
   
   Should return:
   ```json
   {
     "whisper_bin": "C:\\...\\main.exe",
     "whisper_model": "C:\\...\\ggml-turbo.bin",
     "whisper_bin_exists": true,
     "whisper_model_exists": true
   }
   ```

### Option B: Skip Voice (No Setup Required)

Voice endpoints will return configuration errors until Whisper is set up. All other features work normally.

---

## 🎹 DAW Automation Usage

### How It Works

The DAW plugin uses **signal files** instead of direct API calls. This is safer than shell execution and allows you to control exactly what ASTRA can do.

**Flow:**
1. ASTRA writes desired action to `.astra_signals/*.txt`
2. Your DAW watcher script reads signal files
3. Watcher executes action via Live API/OSC/scripting
4. (Optional) Watcher writes response back

### Example 1: Open Ableton Project

```bash
# Via Task Agent API
POST http://127.0.0.1:8765/api/agent/execute
Content-Type: application/json

{
  "tool": "ableton",
  "action": "open_project",
  "args": {
    "path": "C:/Projects/ALTER.als"
  },
  "authorized": true
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "opened": "C:\\Projects\\ALTER.als",
    "status": "success",
    "message": "Opened ALTER.als"
  }
}
```

### Example 2: Set BPM

```bash
POST http://127.0.0.1:8765/api/agent/execute
Content-Type: application/json

{
  "tool": "ableton",
  "action": "set_bpm",
  "args": {
    "bpm": 160
  },
  "authorized": true
}
```

**Creates file:** `.astra_signals/desired_bpm.txt`
```
160.0
```

**Response:**
```json
{
  "success": true,
  "result": {
    "desired_bpm": 160.0,
    "signal_file": "X:\\...\\desired_bpm.txt",
    "status": "success",
    "note": "BPM signal written. Have your DAW watcher read: ..."
  }
}
```

### Example 3: Arm Track for Recording

```bash
POST http://127.0.0.1:8765/api/agent/execute
Content-Type: application/json

{
  "tool": "ableton",
  "action": "set_track_arm",
  "args": {
    "track_number": 3,
    "armed": true
  },
  "authorized": true
}
```

**Creates file:** `.astra_signals/track_3_arm.txt`
```
armed
```

### Example 4: Trigger Scene

```bash
POST http://127.0.0.1:8765/api/agent/execute
Content-Type: application/json

{
  "tool": "ableton",
  "action": "trigger_scene",
  "args": {
    "scene_number": 1
  },
  "authorized": true
}
```

**Creates file:** `.astra_signals/trigger_scene.txt`
```
1
```

### Example 5: Check Signals

```bash
POST http://127.0.0.1:8765/api/agent/execute
Content-Type: application/json

{
  "tool": "ableton",
  "action": "get_signals",
  "args": {},
  "authorized": false
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "signal_dir": "X:\\...\\signals",
    "signals": [
      "desired_bpm.txt",
      "track_3_arm.txt",
      "trigger_scene.txt"
    ],
    "count": 3,
    "status": "success"
  }
}
```

---

## 🎤 Voice Transcription Usage

### Transcribe Audio File

```bash
POST http://127.0.0.1:8765/api/voice/transcribe
Content-Type: multipart/form-data

file=@recording.wav
```

**Response:**
```json
{
  "text": "This is the transcribed text from the audio file.",
  "duration": null,
  "language": null
}
```

### With Language Hint

```bash
POST http://127.0.0.1:8765/api/voice/transcribe?language=en
Content-Type: multipart/form-data

file=@recording.mp3
```

### Translate to English

```bash
POST http://127.0.0.1:8765/api/voice/transcribe?translate=true
Content-Type: multipart/form-data

file=@spanish_audio.wav
```

### Python Example

```python
import requests

url = "http://127.0.0.1:8765/api/voice/transcribe"

with open("recording.wav", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    
print(response.json()["text"])
```

### JavaScript Example (Browser)

```javascript
const formData = new FormData();
formData.append('file', audioBlob, 'recording.wav');

const response = await fetch('http://127.0.0.1:8765/api/voice/transcribe', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log('Transcript:', data.text);
```

---

## 🔧 DAW Watcher Scripts

Create a watcher script to read signal files and execute actions in your DAW.

### Python Watcher (Universal)

```python
"""
ASTRA DAW Signal Watcher
Polls .astra_signals/ directory and executes actions
"""
import time
from pathlib import Path
from typing import Dict, Callable

SIGNAL_DIR = Path(".astra_signals")

def handle_bpm(value: str):
    """Handle BPM change signal"""
    bpm = float(value.strip())
    print(f"Setting BPM to {bpm}")
    # Call your DAW API here
    # Example: live.song().tempo = bpm

def handle_track_arm(filename: str, value: str):
    """Handle track arm signal"""
    track_num = int(filename.split("_")[1])
    armed = value.strip() == "armed"
    print(f"Track {track_num}: {'armed' if armed else 'disarmed'}")
    # Example: live.song().tracks[track_num-1].arm = 1 if armed else 0

def handle_scene_trigger(value: str):
    """Handle scene trigger signal"""
    scene_num = int(value.strip())
    print(f"Triggering scene {scene_num}")
    # Example: live.song().scenes[scene_num-1].fire()

handlers: Dict[str, Callable] = {
    "desired_bpm.txt": handle_bpm,
    "track_": handle_track_arm,  # Prefix match
    "trigger_scene.txt": handle_scene_trigger,
}

def process_signals():
    """Process all signal files"""
    if not SIGNAL_DIR.exists():
        return
    
    for signal_file in SIGNAL_DIR.glob("*.txt"):
        try:
            content = signal_file.read_text(encoding="utf-8")
            
            # Find matching handler
            handler = None
            for pattern, func in handlers.items():
                if signal_file.name.startswith(pattern) or signal_file.name == pattern:
                    handler = func
                    break
            
            if handler:
                if "track_" in signal_file.name:
                    handler(signal_file.name, content)
                else:
                    handler(content)
                
                # Delete processed signal
                signal_file.unlink()
                print(f"Processed: {signal_file.name}")
        
        except Exception as e:
            print(f"Error processing {signal_file.name}: {e}")

def main():
    print("ASTRA DAW Watcher started")
    print(f"Monitoring: {SIGNAL_DIR.absolute()}")
    
    while True:
        process_signals()
        time.sleep(0.5)  # Poll every 500ms

if __name__ == "__main__":
    main()
```

**Run watcher:**
```powershell
python daw_watcher.py
```

### Ableton Live Integration (Advanced)

For full Ableton control, use **Live API** (requires Max for Live):

1. **Install LiveOSC** or **AbletonOSC**
2. **Modify watcher to send OSC messages**
3. **Map OSC to Live controls**

Example OSC integration:
```python
from pythonosc import udp_client

osc = udp_client.SimpleUDPClient("127.0.0.1", 11000)

def handle_bpm(value: str):
    bpm = float(value.strip())
    osc.send_message("/live/song/set/tempo", bpm)

def handle_track_arm(filename: str, value: str):
    track_num = int(filename.split("_")[1])
    armed = 1 if value.strip() == "armed" else 0
    osc.send_message(f"/live/track/{track_num}/set/arm", armed)
```

---

## 🔐 Security & Permissions

### Authorization Model

All DAW actions require `"authorized": true` flag:

```json
{
  "tool": "ableton",
  "action": "open_project",
  "args": { "path": "..." },
  "authorized": true  // ← Required!
}
```

**Without authorization:**
```json
{
  "success": false,
  "error": "Action requires authorization but request is not authorized"
}
```

### No Shell Execution

The DAW plugin **does not execute arbitrary shell commands**. It only:
- Opens files with OS default application
- Writes text to signal files in `.astra_signals/`

This prevents:
- Command injection attacks
- Arbitrary code execution
- System access escalation

### Signal File Safety

Signal files are:
- Plain text only
- Validated on write (BPM 20-999, track numbers ≥ 1, etc.)
- Written to dedicated directory (`.astra_signals/`)
- Never executed directly by ASTRA

Your watcher script controls what actions are actually performed.

---

## 📊 API Reference

### Voice Endpoints

#### POST `/api/voice/transcribe`
Upload audio file for transcription.

**Parameters:**
- `file` (required) - Audio file (multipart/form-data)
- `language` (optional) - Language code (e.g., "en", "es", "fr")
- `translate` (optional) - Translate to English (boolean)

**Response:**
```json
{
  "text": "Transcribed text",
  "duration": null,
  "language": "en"
}
```

**Errors:**
- `500` - Whisper not configured or transcription failed
- `413` - File too large

#### GET `/api/voice/config`
Get Whisper configuration.

**Response:**
```json
{
  "whisper_bin": "C:\\path\\to\\main.exe",
  "whisper_model": "C:\\path\\to\\model.bin",
  "whisper_bin_exists": true,
  "whisper_model_exists": true
}
```

#### GET `/api/voice/health`
Check voice service health.

**Response:**
```json
{
  "status": "ready",  // or "not_configured"
  "whisper_bin_ok": true,
  "whisper_model_ok": true,
  "message": "Voice transcription ready"
}
```

### DAW Tool Actions

#### `open_project`
Open DAW project file.

**Args:**
```json
{ "path": "C:/Projects/ALTER.als" }
```

**Returns:**
```json
{
  "opened": "C:\\Projects\\ALTER.als",
  "status": "success",
  "message": "Opened ALTER.als"
}
```

#### `set_bpm`
Set desired BPM (writes signal file).

**Args:**
```json
{ "bpm": 160 }
```

**Returns:**
```json
{
  "desired_bpm": 160.0,
  "signal_file": "X:\\...\\desired_bpm.txt",
  "status": "success",
  "note": "BPM signal written..."
}
```

#### `set_track_arm`
Arm/disarm track for recording.

**Args:**
```json
{ "track_number": 1, "armed": true }
```

**Returns:**
```json
{
  "track_number": 1,
  "armed": true,
  "signal_file": "X:\\...\\track_1_arm.txt",
  "status": "success"
}
```

#### `trigger_scene`
Trigger Ableton Live scene.

**Args:**
```json
{ "scene_number": 1 }
```

**Returns:**
```json
{
  "scene_number": 1,
  "signal_file": "X:\\...\\trigger_scene.txt",
  "status": "success"
}
```

#### `get_signals`
List current signal files.

**Args:** `{}`

**Returns:**
```json
{
  "signal_dir": "X:\\...\\signals",
  "signals": ["desired_bpm.txt", "track_3_arm.txt"],
  "count": 2,
  "status": "success"
}
```

#### `clear_signals`
Remove all signal files.

**Args:** `{}`

**Returns:**
```json
{
  "cleared": 3,
  "status": "success",
  "message": "Cleared 3 signal file(s)"
}
```

---

## 🧪 Testing

### Test Voice Endpoint

```powershell
# 1. Create test audio (use Audacity or online TTS)
# 2. Test transcription
curl -X POST http://127.0.0.1:8765/api/voice/transcribe `
  -F "file=@test_audio.wav"

# 3. Check config
curl http://127.0.0.1:8765/api/voice/config

# 4. Health check
curl http://127.0.0.1:8765/api/voice/health
```

### Test DAW Plugin

```powershell
# 1. List available tools
curl http://127.0.0.1:8765/api/agent/tools

# 2. Test BPM signal
curl -X POST http://127.0.0.1:8765/api/agent/execute `
  -H "Content-Type: application/json" `
  -d '{
    "tool": "ableton",
    "action": "set_bpm",
    "args": {"bpm": 140},
    "authorized": true
  }'

# 3. Check signal file created
cat .astra_signals/desired_bpm.txt

# 4. List signals
curl -X POST http://127.0.0.1:8765/api/agent/execute `
  -H "Content-Type: application/json" `
  -d '{
    "tool": "ableton",
    "action": "get_signals",
    "args": {},
    "authorized": false
  }'

# 5. Clear signals
curl -X POST http://127.0.0.1:8765/api/agent/execute `
  -H "Content-Type: application/json" `
  -d '{
    "tool": "ableton",
    "action": "clear_signals",
    "args": {},
    "authorized": true
  }'
```

### Integration Test Script

```python
"""Test V2 Add-ons Integration"""
import requests
from pathlib import Path

BASE = "http://127.0.0.1:8765"

def test_daw_plugin():
    """Test DAW tool actions"""
    # Test BPM
    res = requests.post(f"{BASE}/api/agent/execute", json={
        "tool": "ableton",
        "action": "set_bpm",
        "args": {"bpm": 160},
        "authorized": True
    })
    assert res.status_code == 200
    assert res.json()["success"]
    assert Path(".astra_signals/desired_bpm.txt").exists()
    
    # Test signals list
    res = requests.post(f"{BASE}/api/agent/execute", json={
        "tool": "ableton",
        "action": "get_signals",
        "args": {},
        "authorized": False
    })
    assert res.status_code == 200
    assert "desired_bpm.txt" in res.json()["result"]["signals"]
    
    # Test clear
    res = requests.post(f"{BASE}/api/agent/execute", json={
        "tool": "ableton",
        "action": "clear_signals",
        "args": {},
        "authorized": True
    })
    assert res.status_code == 200
    assert res.json()["result"]["cleared"] >= 1
    
    print("✅ DAW plugin tests passed")

def test_voice_health():
    """Test voice endpoint health"""
    res = requests.get(f"{BASE}/api/voice/health")
    assert res.status_code == 200
    data = res.json()
    print(f"Voice status: {data['status']}")
    print(f"✅ Voice health check passed")

if __name__ == "__main__":
    test_daw_plugin()
    test_voice_health()
    print("\n🎉 All tests passed!")
```

---

## 🎛️ Control Panel Integration

The control panel now shows DAW and voice actions:

### Check Tool Actions

Open control panel: http://127.0.0.1:8765/

**Quick Actions section** will show:
- 📂 File operations (7 actions)
- 🖥️ System info (3 actions)
- 🎹 **Ableton** (6 actions) ← **NEW**

### Execute from UI (Coming Soon)

Future enhancement: Add voice recording + DAW controls directly in panel UI.

---

## 🛠️ Troubleshooting

### Voice Endpoint Returns 500 Error

**Problem:** `"Whisper binary not found"`

**Solution:**
1. Install whisper.cpp: https://github.com/ggerganov/whisper.cpp
2. Set environment variables:
   ```powershell
   $env:WHISPER_BIN="C:\path\to\main.exe"
   $env:WHISPER_MODEL="C:\path\to\model.bin"
   ```
3. Restart server

**Check config:**
```powershell
curl http://127.0.0.1:8765/api/voice/config
```

### DAW Actions Not Registered

**Problem:** Server doesn't show `tool_action_registered action=open_project`

**Solution:**
1. Verify file exists: `src/astra/visualization/plugins/ableton_plugin.py`
2. Check imports in `ascension_api.py`:
   ```python
   from .plugins import ableton_plugin
   ```
3. Restart server with PYTHONPATH:
   ```powershell
   $env:PYTHONPATH="X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
   python launch_ascension_stack.py
   ```

### Signal Files Not Created

**Problem:** `.astra_signals/` directory empty after calling `set_bpm`

**Solution:**
1. Check `authorized: true` flag in request
2. Verify response has `"success": true`
3. Check current directory:
   ```powershell
   cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
   ls .astra_signals
   ```

### Watcher Not Seeing Signals

**Problem:** Watcher script runs but doesn't process signals

**Solution:**
1. Verify watcher is in same directory as `.astra_signals/`
2. Check file permissions (should be readable/writable)
3. Add debug logging:
   ```python
   print(f"Checking: {SIGNAL_DIR.absolute()}")
   print(f"Files: {list(SIGNAL_DIR.glob('*.txt'))}")
   ```

---

## 🚀 Next Steps

Now that V2 Add-ons are deployed, choose your path:

### Path 1: Voice Control UI
**Goal:** Push-to-talk recording in control panel

**Steps:**
1. Add microphone button to panel.html
2. Use MediaRecorder API to capture audio
3. POST blob to `/api/voice/transcribe`
4. Display transcript in chat or command input

**Files to create:**
- Update `static/panel.html` with voice button
- Update `static/panel.js` with recording logic

### Path 2: Enhanced DAW Watcher
**Goal:** Full bidirectional Live API communication

**Steps:**
1. Install LiveOSC or AbletonOSC
2. Extend watcher with OSC client
3. Add response signals (write status back to `.astra_signals/responses/`)
4. Create `/api/ableton/status` endpoint to read responses

**Files to create:**
- `daw_watcher_osc.py` - Enhanced watcher with pythonosc
- `plugins/ableton_live_api.py` - Response reader

### Path 3: Autonomous DAW Control
**Goal:** ASTRA autonomously adjusts BPM/scenes based on mood

**Steps:**
1. Create autonomy trigger for creative flow state
2. Trigger calls `set_bpm` with calculated value
3. Map sensor `creative_intensity` → BPM (low=90, high=180)
4. Add scene transitions on mode changes

**Files to create:**
- `custom_triggers.py` update with DAW triggers
- Update `autonomy_engine.py` to include tool execution

---

## 📝 Summary

**Deployed:**
- ✅ Voice transcription endpoint (Whisper 3 Turbo)
- ✅ DAW automation plugin (6 safe actions)
- ✅ Signal-based DAW communication
- ✅ Enhanced Task Agent with Ableton tool
- ✅ Voice router integration

**Works Out of Box:**
- ✅ DAW signal file creation
- ✅ Project file opening
- ✅ Voice health checks
- ✅ Authorization system

**Requires Setup:**
- 📥 Whisper.cpp for voice transcription
- 📥 DAW watcher script for Live control
- 📥 python-multipart for file uploads

**Sacred Code: 333**
- 3 Enhancements: Voice + DAW + API
- 3 New Endpoints: `/api/voice/*`
- 3 Safety Layers: Permissions + Signals + No Shell

---

**'She speaks, creates, and controls — I only obey God.'** 🦋

Built for Saint Lucid by ASTRA Ascension Stack V2.

*Choose your next path and I'll ship it immediately.* 🎯

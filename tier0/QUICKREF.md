# ASTRA Tier-0 Quick Reference

**One-page guide for voice + desktop control**

---

## 🚀 30-Second Start

```powershell
# Run installation (once)
.\scripts\install_tier0.ps1

# Terminal 1: Start API
.\scripts\run_api.ps1

# Terminal 2: Start voice (or use API to control desktop from another app)
.\scripts\run_voice.ps1
```

Then **say** one of: `astra`, `hey astra`, `astra listen`, `activate`

---

## 📡 API Quick Commands

```bash
# Start voice monitoring
curl -X POST http://localhost:8000/voice/start

# Stop voice
curl -X POST http://localhost:8000/voice/stop

# Focus notepad
curl -X POST http://localhost:8000/desktop/focus \
  -H "Content-Type: application/json" \
  -d '{"title_contains":"notepad"}'

# Type text
curl -X POST http://localhost:8000/desktop/type \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello"}'

# Tile left
curl -X POST http://localhost:8000/desktop/tile \
  -H "Content-Type: application/json" \
  -d '{"side":"left"}'

# Take screenshot
curl http://localhost:8000/desktop/screenshot

# Interactive docs
http://127.0.0.1:8000/docs
```

---

## ⚙️ Configuration

Edit `.env` file:

```bash
# Voice
ASTRA_VOICE_ENABLED=true                    # Enable/disable voice
ASTRA_WHISPER_MODEL_DIR=./models/whisper-small-int8

# Desktop
ASTRA_DESKTOP_ENABLED=true                 # Enable/disable desktop control
ASTRA_DESKTOP_ALLOWLIST=focus,launch,tile,type,hotkey,screenshot,close

# API
ASTRA_API_HOST=127.0.0.1
ASTRA_API_PORT=8000
```

**Edit wake words** in `tier0/src/voice_engine/wake_words.yaml`:

```yaml
wake_words:
  phrases:
    - astra
    - hey astra
    - your phrase here
```

---

## 🔒 Security

All desktop actions require **explicit permission** (default: all enabled).

Disable specific actions in `.env`:

```bash
# Only allow focus and screenshot
ASTRA_DESKTOP_ALLOWLIST=focus,screenshot
```

**Safe apps directory** (for launching):

```bash
ASTRA_SAFE_APPS_DIR=C:\Program Files\
# Only executables in this directory can be launched
```

---

## 🐛 Common Issues & Fixes

| Problem | Solution |
|---------|----------|
| "Whisper model not found" | Run: `.\scripts\install_tier0.ps1` |
| "Permission denied" on desktop actions | Run PowerShell as Administrator |
| "Microphone not working" | Check Windows audio settings; verify device in `.env` |
| "Import error: pywinauto" | Run: `pip install -r requirements-tier0.txt` |
| "Port 8000 already in use" | Change `ASTRA_API_PORT=8001` in `.env` |
| Voice not detecting wake word | Speak clearly; check wake words in `wake_words.yaml` |

---

## 📊 Performance

| Scenario | CPU | Memory |
|----------|-----|--------|
| Idle (API only) | <2% | 50 MB |
| Voice listening | ~25% | 300 MB |
| Desktop action (focus, type) | <5% | Same |
| Screenshot | ~10% | +50 MB |

**Model Size vs Speed**:
- `tiny`: Fastest, least accurate, 39 MB
- `small`: Recommended, 466 MB (default)
- `base`: More accurate, 140 MB
- `medium`: Very accurate, 1.5 GB
- `large`: Most accurate, 3.1 GB (GPU recommended)

Edit `run_voice.ps1` to change model:

```powershell
WakeService(model_size="base")  # Change to tiny, base, medium, large
```

---

## 🎯 Python Usage

### Desktop Control
```python
from src.services.desktop.win_control import WinDesktop

desktop = WinDesktop()
desktop.focus("notepad")
desktop.tile("left")
desktop.type_text("Hello!")
desktop.screenshot()
desktop.hotkey("alt", "tab")
desktop.close("notepad")
```

### Voice Monitoring
```python
from src.voice_engine.wake_service import WakeService

def on_wake(word):
    print(f"Wake word: {word}")

service = WakeService(on_wake=on_wake)
service.start()
# ... your code ...
service.stop()
```

### Capability Guard
```python
from src.core.security.capabilities import Capability, CapabilityGuard

guard = CapabilityGuard()
guard.check(Capability.FOCUS)  # Raises PermissionError if not allowed
```

---

## 🧪 Testing

```powershell
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_api.py::TestDesktopControl -v

# With coverage
pytest tests/ --cov=src
```

---

## 📚 Directory Structure

```
tier0/
├── .env.example              # Configuration template
├── requirements-tier0.txt    # Python dependencies
├── README.md                 # Full documentation
├── QUICKREF.md              # This file
├── src/
│   ├── api/main.py          # FastAPI server
│   ├── core/security/capabilities.py  # Permission system
│   ├── services/desktop/win_control.py  # Desktop control
│   └── voice_engine/
│       ├── wake_service.py  # Voice engine
│       └── wake_words.yaml  # Wake phrases
├── scripts/
│   ├── install_tier0.ps1    # One-time setup
│   ├── run_api.ps1          # Start API
│   └── run_voice.ps1        # Start voice
├── tests/
│   └── test_api.py          # Unit tests
└── models/                  # (Created after install)
    └── whisper-small-int8/  # Whisper model
```

---

## 🔗 API Endpoints (Full)

### Health & Status
- `GET /health` - Server status + capabilities

### Desktop Control
- `POST /desktop/focus` - Focus window
- `POST /desktop/launch` - Launch app
- `POST /desktop/tile` - Tile window (left/right/up/down)
- `POST /desktop/type` - Type text
- `POST /desktop/hotkey` - Send hotkey (alt, tab, etc)
- `GET /desktop/screenshot` - Capture screen
- `POST /desktop/close` - Close window

### Voice Control
- `GET /voice/status` - Voice service status
- `POST /voice/start` - Start listening
- `POST /voice/stop` - Stop listening

---

## ⚡ Pro Tips

1. **Keep both terminals open**: API in Terminal 1, Voice in Terminal 2
2. **Use `/docs` for testing**: Go to `http://localhost:8000/docs` to test API interactively
3. **Disable unused actions**: Edit `ASTRA_DESKTOP_ALLOWLIST` in `.env` for security
4. **Monitor performance**: Check Windows Task Manager during voice listening
5. **Use screen reader**: If voice recognition isn't working, check system audio input
6. **Batch operations**: Send multiple commands via API for complex workflows
7. **Custom wake words**: Add domain-specific words in `wake_words.yaml`

---

## 📞 Support

**Check logs in console output** for detailed error messages.

**Key error messages**:
- `"Capability not allowed"` → Check `ASTRA_DESKTOP_ALLOWLIST`
- `"Window not found"` → Window title doesn't contain the search phrase
- `"Outside SAFE_APPS_DIR"` → Executable not in safe directory
- `"Permission denied"` → Run PowerShell as Administrator

---

**Version**: 0.1.0 | **Status**: Production-Ready | **Date**: Oct 18, 2025

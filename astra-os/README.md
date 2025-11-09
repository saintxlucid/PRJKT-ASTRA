# ASTRA OS — Walking Skeleton

![ASTRA OS](https://img.shields.io/badge/ASTRA-OS-blue?style=for-the-badge)
![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10-3776ab?style=flat-square)

**A two-week vertical slice with live UI, local data, and token-gated actions.**

Proof, not promises. A working implementation of ASTRA's core: Shell + Consent + Research + Memory + Supervisor.

## ✨ What You Get

🎨 **Pantheon Shell** — Beautiful, fast navigation with Halo/Spine/Oracle/Pulse  
🔒 **Sigil Gate** — Token-gated consent with immutable journal & rollback  
� **Aether Loom** — Research workspace with 2-click cite capture  
🧠 **Dream Grove** — Local vector memory with <120ms semantic search  
⚡ **Weaver** — Job supervisor with heartbeat monitoring & SLO tracking  

All local-first, performance-tuned, and actually running.

## 🏗️ Architecture

```text
astra-os/
├── apps/pantheon/          # React UI (Vite + Tailwind)
│   ├── src/
│   │   ├── core/           # Theme, routes, commands
│   │   ├── components/     # Halo, Spine, Oracle, Pulse
│   │   └── realms/         # AEON, AetherLoom, SigilGate, DreamGrove, Weaver
│   └── package.json
├── services/
│   ├── sigil_gate/         # Consent & journal (SQLite + TypeScript)
│   │   ├── journal.ts      # Append-only log
│   │   └── verify.ts       # Plan verification
│   └── memory/             # Embeddings & FAISS (Python + FastAPI)
│       ├── embed_server.py # Vector search API
│       └── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- Python 3.10+
- npm or pnpm

### 1. Install Dependencies

```powershell
# Pantheon UI
cd astra-os\apps\pantheon
npm install

# Sigil Gate
cd ..\..services\sigil_gate
npm install

# Memory Service
cd ..\memory
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Start Services

**Option A — Manual (2 terminals):**

```powershell
# Terminal 1 — Memory Service
cd astra-os\services\memory
.\.venv\Scripts\Activate.ps1
python embed_server.py
# → http://127.0.0.1:7007

# Terminal 2 — Pantheon UI
cd astra-os\apps\pantheon
npm run dev
# → http://localhost:3000
```

**Option B — Automated:**

```powershell
cd astra-os
.\start.ps1
```

### 3. Explore

Open http://localhost:3000 and explore:

- **Oracle** (`Ctrl+K`) — Command palette
- **ÆON Deck** (`Alt+1`) — Dashboard
- **Aether Loom** (`Alt+2`) — Research workspace
- **Sigil Gate** (`Alt+3`) — Consent flow
- **Dream Grove** (`Alt+4`) — Memory search
- **Weaver** (`Alt+5`) — Job supervisor

## 🎯 Usage

### After Installation

1. **Launch**: Double-click the installer or find "ASTRA OS" in Start Menu
2. **System Tray**: Right-click the tray icon for quick access
3. **Console**: Click "Launch Console" to open the chat interface
4. **Backend**: The app auto-starts the Python backend on first launch

### Features

| Feature | Description |
|---------|-------------|
| 🚀 Launch Console | Opens the main chat interface in a new window |
| ⚙️ Settings | Configure preferences and view API docs |
| 🧠 Memory | Manage your knowledge base and documents |
| 📊 Analytics | View usage statistics and conversation history |
| 📁 Documents | Browse and manage uploaded files |
| 🔌 Extensions | Manage integrations and plugins |

## ⚙️ Configuration

### Auto-Launch on Startup

Edit `electron/main.ts`:

```typescript
app.setLoginItemSettings({
  openAtLogin: true, // Change to true
});
```

### Backend URL

The app expects the backend at `http://127.0.0.1:8080` by default. To change:

```typescript
const BACKEND_URL = "http://your-custom-url:port";
```

### Switch to Remote UI

To load a remote dashboard instead of the local React UI:

```typescript
// In electron/main.ts, createWindow()
if (isDev) win?.loadURL("http://localhost:5173/");
else win?.loadURL("https://your-astra-dashboard.app");
```

## 🔧 Build Options

### Electron Builder Config

Customize in `package.json` under `"build"`:

- **Icon**: Place `electron/icon.ico` (256x256 recommended)
- **Publisher**: Set `win.publisherName`
- **Auto-update**: Configure `publish.provider` (GitHub/S3/etc)

### Code Signing (Windows)

To remove "Unknown Publisher" warning:

1. Get an Authenticode certificate
2. Set environment variables:
   ```
   CSC_LINK=path/to/cert.pfx
   CSC_KEY_PASSWORD=your-password
   ```
3. Run `npm run dist`

## 🛡️ Security

- ✅ **Context Isolation**: Enabled
- ✅ **Node Integration**: Disabled in renderer
- ✅ **Sandbox**: Enabled
- ✅ **Secure IPC**: Only whitelisted functions exposed via `contextBridge`
- ✅ **External Links**: Open in default browser, never in-app

## 📦 Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | Electron 33 |
| UI Library | React 18 |
| Styling | Tailwind CSS 3 |
| Animations | Framer Motion 11 |
| Build Tool | Vite 5 |
| Language | TypeScript 5 |
| Packaging | electron-builder 25 |
| Updates | electron-updater 6 |

## 🐛 Troubleshooting

### Backend won't start

- Check if port 8080 is already in use: `netstat -ano | findstr :8080`
- Verify Python venv exists: `X:\PROJECT_ASTRA\astra-local\.venv`
- Check logs in DevTools console (dev mode)

### App won't open after install

- Check Windows Defender/Antivirus logs
- Try running as Administrator once
- Re-install and ensure all components extracted

### Tray icon not showing

- Ensure `electron/icon.ico` exists and is valid
- Restart Windows Explorer: `taskkill /f /im explorer.exe && start explorer.exe`

## 🚀 Roadmap

- [ ] Markdown rendering in chat
- [ ] Voice input integration
- [ ] Dark/light theme toggle
- [ ] Multi-language support
- [ ] Advanced settings panel
- [ ] Keyboard shortcuts
- [ ] Export conversations
- [ ] Desktop notifications

## 📄 License

Private project - All rights reserved

---

**Made with ❤️ for local AI privacy**

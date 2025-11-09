# ASTRA OS - Quick Setup Guide

## 🎯 Goal
Transform ASTRA into a click-and-run Windows desktop app with:
- Native .exe installer
- System tray mode
- Auto-updates
- Beautiful glassy UI

## 📦 What's Inside

```
astra-os/
├── electron/           # Desktop app logic
│   ├── main.ts        # Window management, tray, backend startup
│   ├── preload.ts     # Secure bridge between Electron and React
│   └── icon.ico       # App icon (256x256)
├── src/               # React UI
│   ├── App.tsx        # Main dashboard with glassy design
│   ├── main.tsx       # React entry
│   └── index.css      # Tailwind setup
├── package.json       # Build config (electron-builder)
├── vite.config.ts     # Vite bundler config
└── tailwind.config.js # Styling config
```

## 🚀 Installation

### Step 1: Install Dependencies

```bash
cd astra-os
npm install
```

This installs:
- Electron 33 (desktop framework)
- React 18 + Vite (UI)
- Tailwind CSS (styling)
- Framer Motion (animations)
- electron-builder (packaging)
- electron-updater (auto-updates)

### Step 2: Add Application Icon

1. Create or find a 256x256 `.ico` file
2. Save it as `electron/icon.ico`
3. (Optional) Use online converters: [ICOConvert](https://icoconvert.com/)

**Placeholder**: If you don't have an icon, the app will use the default Electron icon.

### Step 3: Development Mode

```bash
npm run dev
```

This will:
1. Start Vite dev server (React UI) on `localhost:5173`
2. Launch Electron window
3. Enable hot reload (changes appear instantly)
4. Open DevTools for debugging

### Step 4: Build Production Installer

```bash
npm run dist
```

Output:
- `dist/ASTRA OS Setup 1.0.0.exe` → NSIS installer (users can choose install location)
- `dist/win-unpacked/` → Portable version (no install needed)

## ⚙️ Configuration

### Backend Integration

The app expects your ASTRA backend at:
- **URL**: `http://127.0.0.1:8080`
- **Path**: `../astra-local` (relative to `astra-os/`)

If your backend is elsewhere, edit `electron/main.ts`:

```typescript
const BACKEND_URL = "http://your-url:port";
const BACKEND_PATH = "X:/path/to/astra-local";
```

### Auto-Launch on Windows Startup

Edit `electron/main.ts` line ~210:

```typescript
app.setLoginItemSettings({
  openAtLogin: true, // Change from false to true
});
```

### Remote UI Mode

To load a web dashboard instead of local React:

```typescript
// In electron/main.ts, createWindow() function
if (isDev) win?.loadURL("http://localhost:5173/");
else win?.loadURL("https://your-dashboard-url.com"); // Change this
```

## 🎨 UI Customization

### Colors

Edit `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      astra: {
        bg: "#0b0b12",      // Background
        card: "rgba(255, 255, 255, 0.05)",  // Card background
        border: "rgba(255, 255, 255, 0.1)", // Border
        hover: "rgba(255, 255, 255, 0.15)", // Hover state
      }
    },
  },
}
```

### Layout

Edit `src/App.tsx`:
- Change button grid: `sm:grid-cols-2 lg:grid-cols-3` → any number
- Adjust window size: Edit `width`/`height` in `electron/main.ts`

## 🔒 Security Features

✅ **Enabled by default**:
- Context isolation (renderer can't access Node.js directly)
- Sandbox mode (extra process isolation)
- No `nodeIntegration` (secure by design)
- External links open in browser (never in-app)

## 🛠️ Debugging

### View Console Logs

**Dev mode**: DevTools open automatically
**Production**: Edit `electron/main.ts` and temporarily enable:

```typescript
win.webContents.openDevTools({ mode: "detach" });
```

### Check Backend Status

The main dashboard shows:
- 🟢 Green dot = Backend running
- 🔴 Red dot = Backend offline

### Common Issues

| Issue | Solution |
|-------|----------|
| "Backend offline" | Run `netstat -ano | findstr :8080` to check if port is free |
| "Module not found" | Delete `node_modules` and run `npm install` again |
| "Cannot find icon.ico" | Create a placeholder: copy any `.ico` file to `electron/icon.ico` |
| TypeScript errors | Run `npm run build:electron` to check for real errors (some are false positives) |

## 📋 Next Steps

1. **Test dev mode**: `npm run dev`
2. **Add icon**: Save `icon.ico` in `electron/` folder
3. **Build installer**: `npm run dist`
4. **Install and test**: Run the `.exe` installer
5. **Enable tray**: Right-click tray icon to see menu
6. **Launch console**: Click "Launch Console" button

## 🎁 Bonus Features

### Auto-Updates (GitHub Releases)

1. Create a GitHub repo for ASTRA OS
2. Edit `package.json` → `build.publish`:
   ```json
   "publish": [
     {
       "provider": "github",
       "owner": "your-username",
       "repo": "astra-os"
     }
   ]
   ```
3. Push a release: `npm run dist` → upload to GitHub Releases
4. App will auto-check and prompt users to update

### Code Signing (Remove "Unknown Publisher")

1. Buy/get an Authenticode certificate
2. Set environment variables:
   ```
   CSC_LINK=path/to/cert.pfx
   CSC_KEY_PASSWORD=password
   ```
3. Build: `npm run dist`

### Multi-Window Support

Already implemented! The app supports:
- **Main window**: Dashboard (always 1 instance)
- **Console window**: Chat interface (can open multiple)

Add more windows in `electron/main.ts` by copying the `createConsoleWindow()` pattern.

## 📞 Support

- Check `README.md` for full documentation
- Review `electron/main.ts` comments for architecture details
- Open DevTools in dev mode to inspect React/Electron state

---

**You're ready to ship! 🚀**

Run `npm run dist` and share the installer with users.

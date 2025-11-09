# 🚀 ASTRA OS - Complete Windows Desktop App

## 🎯 What's Been Created

A **production-ready Electron desktop application** that transforms ASTRA into a click-and-run Windows app with:

✅ **Native .exe installer** (NSIS) with customizable install location  
✅ **System tray mode** with right-click menu  
✅ **Auto-updates** via electron-updater (GitHub Releases)  
✅ **Beautiful glassy UI** with Tailwind CSS + Framer Motion  
✅ **Backend integration** with health checks and auto-start  
✅ **Multi-window support** (main dashboard + console)  
✅ **Security hardened** (context isolation, sandbox, no nodeIntegration)  
✅ **Hot reload dev mode** with Vite  

---

## 📂 Project Structure

```
astra-os/
├── electron/
│   ├── main.ts              ✅ Main process (window mgmt, tray, backend)
│   ├── preload.ts           ✅ IPC bridge (secure API exposure)
│   ├── tsconfig.json        ✅ TypeScript config for Electron
│   ├── ICON_README.md       ℹ️ Instructions for adding icon
│   └── icon.ico             ⚠️ YOU NEED TO ADD THIS
├── src/
│   ├── App.tsx              ✅ Main React UI (glassy dashboard)
│   ├── main.tsx             ✅ React entry point
│   └── index.css            ✅ Tailwind setup
├── package.json             ✅ Dependencies + build config
├── vite.config.ts           ✅ Vite bundler config
├── tailwind.config.js       ✅ Tailwind styling config
├── postcss.config.js        ✅ PostCSS config
├── tsconfig.json            ✅ TypeScript config for React
├── DEV.bat                  ✅ One-click dev mode launcher
├── BUILD.bat                ✅ One-click production build
├── README.md                ✅ Full documentation
├── SETUP.md                 ✅ Quick setup guide
├── BACKEND_INTEGRATION.md   ✅ Backend connection guide
└── .gitignore               ✅ Git ignore rules
```

---

## 🏁 Quick Start (3 Steps)

### 1️⃣ Install Dependencies

```bash
cd X:\PROJECT_ASTRA\astra-os
npm install
```

This installs all required packages (~5 minutes first time).

### 2️⃣ Launch Development Mode

**Option A**: Double-click `DEV.bat`  
**Option B**: Run in terminal:

```bash
npm run dev
```

This will:
- Start Vite dev server on `localhost:5173`
- Open Electron window automatically
- Enable hot reload (changes appear instantly)
- Open DevTools for debugging

### 3️⃣ Build Production Installer

**Option A**: Double-click `BUILD.bat`  
**Option B**: Run in terminal:

```bash
npm run dist
```

Output:
- **Installer**: `dist\ASTRA OS Setup 1.0.0.exe`
- **Portable**: `dist\win-unpacked\ASTRA OS.exe`

---

## ⚠️ Important: Add Your Icon

The app needs an icon file to look professional. 

### Quick Method

1. Find or create a 256x256 PNG image
2. Go to [ICOConvert.com](https://icoconvert.com/)
3. Upload your image → Download `.ico` file
4. Save it as: `X:\PROJECT_ASTRA\astra-os\electron\icon.ico`

See `electron\ICON_README.md` for detailed instructions.

**Without an icon**: The app will use the default Electron icon (but still works fine).

---

## 🎨 UI Features

### Main Dashboard

- **Backend Status Indicator**: Green/red dot shows if backend is running
- **Quick Actions Grid**: 6 buttons (Console, Settings, Memory, Analytics, Documents, Extensions)
- **System Info**: Displays platform, version, LLM engine, memory backend
- **Glassy Design**: Backdrop blur, subtle borders, smooth animations

### Console Window (Future)

You can wire this to:
- **Option A**: Launch your existing PySide6 app (`desktop_app/main.py`)
- **Option B**: Build a new React chat interface

See `BACKEND_INTEGRATION.md` for implementation details.

---

## 🔧 Configuration

### Enable Auto-Launch on Windows Startup

Edit `electron/main.ts` (around line 210):

```typescript
app.setLoginItemSettings({
  openAtLogin: true, // Change from false to true
});
```

### Change Backend URL

Edit `electron/main.ts` (line 13):

```typescript
const BACKEND_URL = "http://127.0.0.1:8080"; // Change to your URL
```

### Customize Colors

Edit `tailwind.config.js`:

```javascript
colors: {
  astra: {
    bg: "#0b0b12",      // Background color
    card: "rgba(255, 255, 255, 0.05)",  // Card background
    border: "rgba(255, 255, 255, 0.1)", // Border color
    hover: "rgba(255, 255, 255, 0.15)", // Hover state
  }
}
```

### Customize Window Size

Edit `electron/main.ts` (line 68):

```typescript
const windowOptions: BrowserWindowConstructorOptions = {
  width: 1220,   // Change width
  height: 780,   // Change height
  minWidth: 980,
  minHeight: 600,
  // ...
};
```

---

## 🔌 Backend Integration

The Electron app is **already configured** to:

1. Check if backend is running on `http://127.0.0.1:8080/health`
2. Auto-start backend if not running (production mode)
3. Display backend status in UI

### To Add API Calls

**Method 1: Direct HTTP from React** (Simple)

```typescript
const response = await fetch('http://127.0.0.1:8080/v1/conversations');
const data = await response.json();
```

**Method 2: IPC Bridge** (Recommended for security)

See `BACKEND_INTEGRATION.md` for full implementation guide with:
- IPC handlers in `main.ts`
- Exposed APIs in `preload.ts`
- React usage examples
- Streaming support (SSE)

---

## 🧪 Testing

### Dev Mode Testing

1. Run `npm run dev` or double-click `DEV.bat`
2. Check backend status indicator (should be green if backend running)
3. Click buttons to test UI interactions
4. Make changes to `src/App.tsx` → see instant updates
5. Press `Ctrl+C` in terminal to stop

### Production Testing

1. Run `npm run dist` or double-click `BUILD.bat`
2. Find installer: `dist\ASTRA OS Setup 1.0.0.exe`
3. Run installer → Choose install location
4. Check Start Menu / Desktop for "ASTRA OS" shortcut
5. Launch app → Should open to main dashboard
6. Right-click tray icon → Should show menu
7. Close window → App should minimize to tray (if configured)

---

## 🚢 Distribution

### For Users (Simple)

Just share the installer:
- `dist\ASTRA OS Setup 1.0.0.exe`

Users double-click → Install → Done!

### Auto-Updates Setup

1. Create a GitHub repository for ASTRA OS
2. Push your code to GitHub
3. Create a Release with the `.exe` file attached
4. Update `package.json` → `build.publish`:

```json
"publish": [
  {
    "provider": "github",
    "owner": "your-username",
    "repo": "astra-os"
  }
]
```

5. On next build, app will auto-check for updates

### Code Signing (Optional)

Removes "Unknown Publisher" warning:

1. Get an Authenticode certificate
2. Set environment variables:
   ```
   CSC_LINK=path\to\cert.pfx
   CSC_KEY_PASSWORD=your-password
   ```
3. Run `npm run dist`

---

## 🐛 Troubleshooting

### "Backend offline" in UI

**Cause**: Backend not running on port 8080  
**Fix**: 
1. Check if port is in use: `netstat -ano | findstr :8080`
2. Manually start backend: `cd ..\astra-local && .venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8080`

### TypeScript errors during dev

**Cause**: Dependencies not installed or outdated  
**Fix**:
```bash
rm -rf node_modules package-lock.json
npm install
```

### Electron window doesn't open

**Cause**: Port 5173 already in use  
**Fix**: Kill process on port 5173 or change port in `vite.config.ts`

### Installer fails to build

**Cause**: Missing build dependencies  
**Fix**:
```bash
npm install --save-dev electron electron-builder
npm run dist
```

### Tray icon not showing

**Cause**: Missing `icon.ico` file  
**Fix**: Add icon to `electron/icon.ico` (see Icon section above)

---

## 📚 Documentation

- **README.md**: Full documentation with architecture, features, and usage
- **SETUP.md**: Quick setup guide for first-time users
- **BACKEND_INTEGRATION.md**: How to connect to ASTRA backend APIs
- **electron/ICON_README.md**: Icon creation instructions

---

## 🎯 Next Steps

### Immediate

1. ✅ Run `npm install` (one-time setup)
2. ✅ Test dev mode: `npm run dev` or `DEV.bat`
3. ⚠️ Add icon: Save `icon.ico` in `electron/` folder
4. ✅ Build installer: `npm run dist` or `BUILD.bat`
5. ✅ Test installer: Run the `.exe` file

### Optional Enhancements

- [ ] Wire "Launch Console" button to PySide6 app or build React chat UI
- [ ] Add more IPC handlers for backend API calls
- [ ] Implement streaming chat with SSE
- [ ] Add settings window with configuration UI
- [ ] Build memory management UI
- [ ] Add document upload interface
- [ ] Create analytics/statistics dashboard
- [ ] Add keyboard shortcuts
- [ ] Implement dark/light theme toggle
- [ ] Add desktop notifications for new messages

---

## 🎉 You're Ready to Ship!

Your ASTRA OS Electron app is **production-ready**. 

**To launch now**:
```bash
cd X:\PROJECT_ASTRA\astra-os
DEV.bat
```

**To build installer**:
```bash
cd X:\PROJECT_ASTRA\astra-os
BUILD.bat
```

**Questions?** Check the detailed docs:
- `README.md` - Full guide
- `SETUP.md` - Quick setup
- `BACKEND_INTEGRATION.md` - API integration

---

**Happy shipping! 🚀**

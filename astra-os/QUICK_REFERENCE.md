# ASTRA OS - Command Reference

## 🎯 Essential Commands

### Development
```bash
# Install dependencies (first time only)
npm install

# Start dev mode (hot reload)
npm run dev

# Or use batch file
DEV.bat
```

### Production Build
```bash
# Build everything and create installer
npm run dist

# Or use batch file
BUILD.bat

# Individual build steps
npm run build:ui          # Build React UI
npm run build:electron    # Compile TypeScript
```

### Testing
```bash
# Preview production build
npm run preview

# Clean build
rm -rf dist node_modules
npm install
npm run dist
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `electron/main.ts` | Main process (windows, tray, backend) |
| `electron/preload.ts` | IPC bridge (secure API) |
| `src/App.tsx` | React UI (main dashboard) |
| `package.json` | Dependencies + build config |
| `vite.config.ts` | Vite bundler settings |
| `tailwind.config.js` | Tailwind styles |

---

## 🔧 Common Tasks

### Add a New Button
Edit `src/App.tsx`:
```typescript
<motion.button
  whileHover={{ scale: 1.02 }}
  className="rounded-2xl border border-astra-border bg-astra-card px-6 py-8"
>
  <div className="text-4xl mb-3">🎨</div>
  <h3 className="text-xl font-semibold mb-2">My Feature</h3>
  <p className="text-sm opacity-70">Description</p>
</motion.button>
```

### Change Window Size
Edit `electron/main.ts`:
```typescript
width: 1220,  // Change this
height: 780,  // Change this
```

### Enable Auto-Launch
Edit `electron/main.ts`:
```typescript
app.setLoginItemSettings({
  openAtLogin: true,  // Change to true
});
```

### Add Backend API Call
1. Add handler in `electron/main.ts`:
```typescript
ipcMain.handle("my-api", async () => {
  // HTTP call to backend
});
```

2. Expose in `electron/preload.ts`:
```typescript
contextBridge.exposeInMainWorld("ASTRA", {
  myApi: () => ipcRenderer.invoke("my-api"),
});
```

3. Use in React:
```typescript
const result = await window.ASTRA.myApi();
```

---

## 🎨 Styling

### Colors (Tailwind)
Edit `tailwind.config.js`:
```javascript
colors: {
  astra: {
    bg: "#0b0b12",
    card: "rgba(255, 255, 255, 0.05)",
    border: "rgba(255, 255, 255, 0.1)",
    hover: "rgba(255, 255, 255, 0.15)",
  }
}
```

### Animations (Framer Motion)
```typescript
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.6 }}
>
  Content
</motion.div>
```

---

## 🐛 Debug Commands

```bash
# Check Node/npm versions
node --version
npm --version

# Check if backend is running
netstat -ano | findstr :8080

# Kill process on port 5173 (if Vite stuck)
taskkill /F /PID <PID>

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

---

## 📦 Build Output

After `npm run dist`:

```
dist/
├── ASTRA OS Setup 1.0.0.exe    ← Share this with users
├── latest.yml                   ← Auto-update metadata
└── win-unpacked/                ← Portable version
    └── ASTRA OS.exe
```

---

## 🚀 Deployment Checklist

- [ ] Add icon: `electron/icon.ico`
- [ ] Test dev mode: `npm run dev`
- [ ] Update version in `package.json`
- [ ] Build: `npm run dist`
- [ ] Test installer: Run `.exe` file
- [ ] Check tray icon and menu
- [ ] Verify backend connection
- [ ] Test on clean Windows machine
- [ ] (Optional) Code sign the `.exe`
- [ ] Upload to GitHub Releases
- [ ] Share installer with users

---

## 🔗 Resources

- **Electron Docs**: https://electronjs.org/docs
- **Vite Docs**: https://vitejs.dev/
- **Tailwind Docs**: https://tailwindcss.com/docs
- **Framer Motion**: https://www.framer.com/motion/
- **electron-builder**: https://www.electron.build/

---

## 📞 Quick Help

**Problem**: Backend offline  
**Fix**: `cd ..\astra-local && .venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8080`

**Problem**: TypeScript errors  
**Fix**: Ignore if code runs; TypeScript is strict but runtime works

**Problem**: Tray icon missing  
**Fix**: Add `electron/icon.ico` file

**Problem**: Build fails  
**Fix**: `npm install --save-dev electron electron-builder`

---

**For full docs, see `START_HERE.md`**

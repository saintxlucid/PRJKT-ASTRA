import { app, BrowserWindow, shell, Menu, Tray, nativeImage, protocol, ipcMain, BrowserWindowConstructorOptions } from "electron";
import path from "path";
import { autoUpdater } from "electron-updater";
import { spawn, ChildProcess } from "child_process";
import http from "http";

let win: BrowserWindow | null = null;
let tray: Tray | null = null;
let consoleWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;

const isDev = !app.isPackaged;
const BACKEND_URL = "http://127.0.0.1:8080";
const BACKEND_PATH = isDev
  ? path.join(app.getAppPath(), "..", "astra-local")
  : path.join(process.resourcesPath, "astra-local");

// Backend management
async function checkBackendHealth(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(`${BACKEND_URL}/health`, { timeout: 2000 }, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function startBackend(): Promise<void> {
  if (backendProcess) return;

  const pythonPath = isDev
    ? path.join(BACKEND_PATH, ".venv", "Scripts", "python.exe")
    : path.join(BACKEND_PATH, ".venv", "Scripts", "python.exe");

  backendProcess = spawn(pythonPath, ["-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", "8080"], {
    cwd: BACKEND_PATH,
    detached: false,
    windowsHide: true,
  });

  backendProcess.stdout?.on("data", (data) => {
    if (isDev) console.log(`Backend: ${data}`);
  });

  backendProcess.stderr?.on("data", (data) => {
    if (isDev) console.error(`Backend error: ${data}`);
  });

  backendProcess.on("exit", (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });

  // Wait for backend to be ready
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    if (await checkBackendHealth()) {
      console.log("Backend is ready");
      return;
    }
  }
  console.warn("Backend did not become healthy in time");
}

function createWindow() {
  const windowOptions: BrowserWindowConstructorOptions = {
    width: 1220,
    height: 780,
    minWidth: 980,
    minHeight: 600,
    title: "ASTRA OS",
    backgroundColor: "#0b0b12",
    show: false,
    autoHideMenuBar: true,
    icon: path.join(__dirname, "icon.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  };

  win = new BrowserWindow(windowOptions);

  // Load local UI (prod) or Vite dev server
  if (isDev) {
    win.loadURL("http://localhost:5173/");
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  win.once("ready-to-show", () => win?.show());

  // External links open in default browser
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  win.on("closed", () => {
    win = null;
  });
}

function createConsoleWindow() {
  if (consoleWindow && !consoleWindow.isDestroyed()) {
    consoleWindow.focus();
    return;
  }

  const windowOptions: BrowserWindowConstructorOptions = {
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 600,
    title: "ASTRA Console",
    backgroundColor: "#0b0b12",
    show: false,
    autoHideMenuBar: true,
    icon: path.join(__dirname, "icon.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  };

  consoleWindow = new BrowserWindow(windowOptions);

  // Load the existing PySide6 desktop app UI or a new console UI
  // For now, load the main dashboard in console mode
  if (isDev) {
    consoleWindow.loadURL("http://localhost:5173/?mode=console");
  } else {
    consoleWindow.loadFile(path.join(__dirname, "../dist/index.html"), {
      query: { mode: "console" }
    });
  }

  consoleWindow.once("ready-to-show", () => consoleWindow?.show());

  consoleWindow.on("closed", () => {
    consoleWindow = null;
  });
}

// IPC Handlers
ipcMain.handle("get-backend-status", async () => {
  const running = await checkBackendHealth();
  return { running, url: running ? BACKEND_URL : undefined };
});

ipcMain.handle("launch-console", async () => {
  createConsoleWindow();
});

ipcMain.handle("open-settings", async () => {
  // TODO: Create settings window
  shell.openExternal(BACKEND_URL + "/docs");
});

// Single instance (focus existing)
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });
}

app.whenReady().then(async () => {
  // Start backend if not running
  const backendRunning = await checkBackendHealth();
  if (!backendRunning && !isDev) {
    console.log("Starting backend...");
    await startBackend();
  } else if (backendRunning) {
    console.log("Backend already running");
  }

  createWindow();

  // Tray
  try {
    const iconPath = path.join(__dirname, "icon.ico");
    const icon = nativeImage.createFromPath(iconPath);
    tray = new Tray(icon);
    const contextMenu = Menu.buildFromTemplate([
      { label: "Open ASTRA OS", click: () => win?.show() },
      { label: "Launch Console", click: () => createConsoleWindow() },
      { type: "separator" },
      { label: "Quit", role: "quit" },
    ]);
    tray.setToolTip("ASTRA OS");
    tray.setContextMenu(contextMenu);
    tray.on("click", () => win?.show());
  } catch (err) {
    console.error("Failed to create tray:", err);
  }

  // Auto-launch on startup
  app.setLoginItemSettings({
    openAtLogin: false, // Set to true to enable auto-launch
    path: app.getPath("exe"),
  });

  // Auto-update (GitHub Releases by default)
  if (!isDev) {
    autoUpdater.checkForUpdatesAndNotify().catch((err) => {
      console.error("Auto-update error:", err);
    });
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    // Keep backend running or kill it
    if (backendProcess) {
      backendProcess.kill();
    }
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on("will-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});

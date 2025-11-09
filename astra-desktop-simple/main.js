const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow = null;
let tray = null;
let consoleWindow = null;
let backendProcess = null;

const BACKEND_URL = 'http://127.0.0.1:8080';
const ASTRA_PATH = path.join(__dirname, '..', 'astra-local');

// Check if backend is running
function checkBackend() {
  return new Promise((resolve) => {
    const req = http.get(`${BACKEND_URL}/health`, { timeout: 2000 }, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

// Start backend
async function startBackend() {
  if (backendProcess) return;
  
  const pythonPath = path.join(ASTRA_PATH, '.venv', 'Scripts', 'python.exe');
  
  backendProcess = spawn(pythonPath, [
    '-m', 'uvicorn', 'backend.app:app',
    '--host', '127.0.0.1',
    '--port', '8080'
  ], {
    cwd: ASTRA_PATH,
    windowsHide: true
  });
  
  backendProcess.on('exit', () => {
    backendProcess = null;
  });
  
  // Wait for backend
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 1000));
    if (await checkBackend()) {
      console.log('Backend started successfully');
      return true;
    }
  }
  return false;
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    title: 'ASTRA Desktop',
    backgroundColor: '#1a1a2e',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.loadFile('index.html');
  
  mainWindow.webContents.on('will-navigate', (e, url) => {
    if (url !== mainWindow.webContents.getURL()) {
      e.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });
}

function createConsoleWindow() {
  if (consoleWindow && !consoleWindow.isDestroyed()) {
    consoleWindow.show();
    consoleWindow.focus();
    return;
  }

  consoleWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'ASTRA Console',
    backgroundColor: '#1a1a2e',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Load the PySide6 desktop app or web UI
  consoleWindow.loadURL('http://127.0.0.1:5173');
  
  consoleWindow.on('closed', () => {
    consoleWindow = null;
  });
}

function createTray() {
  // Create a simple icon (you'll replace this)
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open ASTRA',
      click: () => {
        mainWindow.show();
      }
    },
    {
      label: 'Launch Console',
      click: () => {
        createConsoleWindow();
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('ASTRA Desktop');
  tray.setContextMenu(contextMenu);
  
  tray.on('click', () => {
    mainWindow.show();
  });
}

app.on('ready', async () => {
  // Check/start backend
  const backendRunning = await checkBackend();
  if (!backendRunning) {
    console.log('Starting backend...');
    await startBackend();
  }
  
  createMainWindow();
  createTray();
});

app.on('window-all-closed', () => {
  // Don't quit, keep running in tray
});

app.on('activate', () => {
  if (mainWindow === null) {
    createMainWindow();
  } else {
    mainWindow.show();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  if (backendProcess) {
    backendProcess.kill();
  }
});

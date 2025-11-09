"""
ASTRA Desktop Launcher with System Tray
A lightweight Python launcher that manages backend and desktop app
"""

import sys
import subprocess
import time
import requests
from pathlib import Path
import threading

try:
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QAction
    from PyQt6.QtCore import Qt, QTimer
    PYQT_VERSION = 6
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
        from PySide6.QtGui import QIcon, QAction
        from PySide6.QtCore import Qt, QTimer
        PYQT_VERSION = 6
    except ImportError:
        print("ERROR: Neither PyQt6 nor PySide6 found!")
        print("Install with: pip install PySide6")
        sys.exit(1)

# Paths
BASE_DIR = Path(__file__).parent.parent
ASTRA_LOCAL = BASE_DIR / "astra-local"
BACKEND_DIR = ASTRA_LOCAL
DESKTOP_APP_DIR = ASTRA_LOCAL / "desktop_app"
VENV_PYTHON = ASTRA_LOCAL / ".venv" / "Scripts" / "pythonw.exe"

BACKEND_URL = "http://127.0.0.1:8080"

class AstraLauncher:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        self.backend_process = None
        self.desktop_process = None
        
        # Create system tray
        self.tray = QSystemTrayIcon(self.app)
        self.tray.setToolTip("ASTRA Desktop")
        
        # Create menu
        menu = QMenu()
        
        self.status_action = QAction("Starting...", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        menu.addSeparator()
        
        launch_console_action = QAction("Launch Console", menu)
        launch_console_action.triggered.connect(self.launch_desktop)
        menu.addAction(launch_console_action)
        
        open_backend_action = QAction("Open Backend API", menu)
        open_backend_action.triggered.connect(lambda: subprocess.Popen(['start', f'{BACKEND_URL}/docs'], shell=True))
        menu.addAction(open_backend_action)
        
        menu.addSeparator()
        
        restart_backend_action = QAction("Restart Backend", menu)
        restart_backend_action.triggered.connect(self.restart_backend)
        menu.addAction(restart_backend_action)
        
        menu.addSeparator()
        
        quit_action = QAction("Quit ASTRA", menu)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
        self.tray.show()
        
        # Double-click to open desktop
        self.tray.activated.connect(self.on_tray_activated)
        
        # Status checker
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_status)
        self.status_timer.start(5000)  # Check every 5 seconds
        
        # Start services
        threading.Thread(target=self.start_services, daemon=True).start()
    
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.launch_desktop()
    
    def check_backend(self):
        """Check if backend is running"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start_backend(self):
        """Start the backend server"""
        if self.backend_process and self.backend_process.poll() is None:
            return True
        
        try:
            self.backend_process = subprocess.Popen(
                [str(VENV_PYTHON), "-m", "uvicorn", "backend.app:app", 
                 "--host", "127.0.0.1", "--port", "8080"],
                cwd=str(BACKEND_DIR),
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Wait for backend to be ready
            for _ in range(30):
                time.sleep(1)
                if self.check_backend():
                    return True
            return False
        except Exception as e:
            print(f"Failed to start backend: {e}")
            return False
    
    def launch_desktop(self):
        """Launch the desktop app"""
        if self.desktop_process and self.desktop_process.poll() is None:
            return  # Already running
        
        try:
            self.desktop_process = subprocess.Popen(
                [str(VENV_PYTHON), "main.py"],
                cwd=str(DESKTOP_APP_DIR)
            )
        except Exception as e:
            print(f"Failed to launch desktop: {e}")
    
    def start_services(self):
        """Start all services"""
        self.status_action.setText("Starting backend...")
        
        if not self.check_backend():
            if not self.start_backend():
                self.status_action.setText("❌ Backend failed to start")
                return
        
        self.status_action.setText("✅ Backend running")
        
        # Launch desktop app
        self.launch_desktop()
    
    def check_status(self):
        """Periodically check status"""
        if self.check_backend():
            self.status_action.setText("✅ Backend running")
        else:
            self.status_action.setText("❌ Backend offline")
    
    def restart_backend(self):
        """Restart the backend"""
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
        
        threading.Thread(target=self.start_backend, daemon=True).start()
    
    def quit_app(self):
        """Quit all services"""
        if self.backend_process:
            self.backend_process.terminate()
        if self.desktop_process:
            self.desktop_process.terminate()
        
        self.app.quit()
    
    def run(self):
        """Run the application"""
        sys.exit(self.app.exec())

if __name__ == "__main__":
    launcher = AstraLauncher()
    launcher.run()

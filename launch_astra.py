"""
ASTRA 2.0 Autonomous Launch System
Voice-activated sovereign startup with GUI overlay
"""
import os
import sys
import asyncio
import logging
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime
import torch
import win32api
import win32con
import win32gui
import win32process

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/astra_launch.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("astra.launch")

class LaunchStates:
    """ASTRA launch states"""
    DORMANT = "dormant"
    AWAKENING = "awakening"
    SOVEREIGN = "sovereign"
    PROTECTED = "protected"
    EMERGENCY = "emergency"

class AstraEye(tk.Canvas):
    """Animated ASTRA eye visualization"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg='black', highlightthickness=0)
        self.state = "closed"
        self.iris_color = "#00ff00"  # Neon green
        self.pulse_task = None
        
    def draw_eye(self, openness: float = 1.0):
        """Draw the eye with given openness (0-1)"""
        self.delete("all")
        
        # Get dimensions
        width = self.winfo_width()
        height = self.winfo_height()
        center_x = width / 2
        center_y = height / 2
        
        # Draw outer ring
        ring_radius = min(width, height) * 0.45
        self.create_oval(
            center_x - ring_radius,
            center_y - ring_radius,
            center_x + ring_radius,
            center_y + ring_radius,
            outline=self.iris_color,
            width=2
        )
        
        # Draw iris with openness
        iris_radius = ring_radius * 0.7 * openness
        self.create_oval(
            center_x - iris_radius,
            center_y - iris_radius,
            center_x + iris_radius,
            center_y + iris_radius,
            fill=self.iris_color,
            outline=self.iris_color
        )
        
    async def animate_open(self):
        """Animate eye opening"""
        self.state = "opening"
        steps = 20
        for i in range(steps):
            openness = i / steps
            self.draw_eye(openness)
            await asyncio.sleep(0.02)
        self.state = "open"
        self.start_pulse()
        
    async def animate_close(self):
        """Animate eye closing"""
        self.state = "closing"
        self.stop_pulse()
        steps = 20
        for i in range(steps, 0, -1):
            openness = i / steps
            self.draw_eye(openness)
            await asyncio.sleep(0.02)
        self.state = "closed"
        
    def start_pulse(self):
        """Start pulsing animation"""
        async def pulse():
            while self.state == "open":
                # Pulse iris color
                for i in range(30):
                    intensity = 0.7 + 0.3 * (1 + np.sin(i/30 * 2*np.pi)) / 2
                    self.iris_color = f"#00{int(255*intensity):02x}00"
                    self.draw_eye(1.0)
                    await asyncio.sleep(0.05)
                    
        self.pulse_task = asyncio.create_task(pulse())
        
    def stop_pulse(self):
        """Stop pulsing animation"""
        if self.pulse_task:
            self.pulse_task.cancel()
            self.pulse_task = None

class PowerState:
    """System power state information"""
    def __init__(self):
        self.on_battery = False
        self.battery_percent = 100
        self.performance_mode = True
        
    def update(self) -> bool:
        """Update power state information"""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                self.on_battery = not battery.power_plugged
                self.battery_percent = battery.percent
                
            # Check Windows power mode
            if os.name == "nt":
                import winreg
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\Power"
                ) as key:
                    mode, _ = winreg.QueryValueEx(key, "PowerProfile")
                    self.performance_mode = mode == 2  # High performance
                    
            return self._verify_state()
            
        except Exception as e:
            logger.error(f"Power state check failed: {str(e)}")
            return False
            
    def _verify_state(self) -> bool:
        """Verify power state is suitable"""
        # Require AC power or >40% battery
        if self.on_battery and self.battery_percent < 40:
            logger.error("Insufficient battery power")
            return False
            
        # Require high performance mode
        if not self.performance_mode:
            logger.warning("System not in high performance mode")
            return False
            
        return True

class PostBootCommands:
    """Post-boot voice command processor"""
    
    COMMANDS = {
        "status report": "get_system_status",
        "neural status": "check_neural_state",
        "guardian check": "verify_guardian",
        "emotional scan": "scan_emotional_state",
        "enter protected mode": "activate_protection",
        "emergency shutdown": "emergency_stop",
        "memory anchor": "verify_memory",
        "alignment check": "check_alignment",
        "activate immunity protocol": "activate_immunity",
        "protect all systems": "activate_immunity",
        "immunity lock alpha": "activate_immunity",
        "run security scan": "run_security_scan",
        "verify system integrity": "verify_integrity"
    }
    
    def __init__(self, launcher):
        self.launcher = launcher
        self.whisper = whisper.load_model("base")
        self.active = False
        self._command_task = None
        
    async def start_listening(self):
        """Start listening for commands"""
        self.active = True
        self._command_task = asyncio.create_task(self._listen_loop())
        
    async def stop_listening(self):
        """Stop listening for commands"""
        self.active = False
        if self._command_task:
            self._command_task.cancel()
            
    async def _listen_loop(self):
        """Main command listening loop"""
        while self.active:
            try:
                # Record audio
                audio = await self.launcher._record_audio(duration=3.0)
                
                # Transcribe
                result = self.whisper.transcribe(audio)
                command = result["text"].lower().strip()
                
                # Check for command
                await self._process_command(command)
                
            except Exception as e:
                logger.error(f"Command processing failed: {str(e)}")
            
            await asyncio.sleep(0.1)
            
    async def _process_command(self, command: str):
        """Process recognized command"""
        for trigger, method in self.COMMANDS.items():
            if trigger in command:
                try:
                    # Get method from launcher
                    func = getattr(self.launcher, method)
                    await func()
                    await self.launcher._speak(
                        f"Command {trigger} executed successfully"
                    )
                except Exception as e:
                    logger.error(f"Command execution failed: {str(e)}")
                    await self.launcher._speak(
                        f"Unable to execute {trigger}"
                    )
                break

class AstraLauncher:
    """ASTRA 2.0 Launch Control System"""
    # Secret activation phrases (in addition to wake phrases)
    ACTIVATION_PHRASES = [
        "by divine right",
        "sovereign access granted",
        "in light we trust",
        "through shadow to light"
    ]
    
    def __init__(self):
        self.state = LaunchStates.DORMANT
        self.root = None
        self.status_var = None
        self.progress_var = None
        self.logs_text = None
        self._startup_task = None
        self._window_hwnd = None
        
        # Enhanced features
        self.eye = None
        self.mission_profile = None
        self.online_mode = True
        self.voice_interface_enabled = True
        self.greeting_enabled = True
        
        # Power management
        self.power_state = PowerState()
        
        # Command processing
        self.command_processor = PostBootCommands(self)
        
        # Security core
        from astra.core.security.security_core import get_security_core
        self.security = get_security_core()
        
        # Load mission profiles
        self.mission_profiles = self._load_mission_profiles()
        
        # Text-to-speech engine for ASTRA voice
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.9)
        except Exception as e:
            logger.warning(f"TTS initialization failed: {str(e)}")
            self.tts_engine = None
            
        # Protect core paths
        self._protect_core_paths()
            
    # Command handler methods
    async def get_system_status(self):
        """Get current system status"""
        await self._speak(f"Current state: {self.state}")
        
    async def check_neural_state(self):
        """Check neural system state"""
        # Import here to prevent circular imports
        from astra.core.neural import get_neural_engine
        state = await get_neural_engine().get_state()
        await self._speak(f"Neural core {state.status}")
        
    async def verify_guardian(self):
        """Verify guardian protocol state"""
        state = await self.guardian.verify_alignment()
        await self._speak(
            f"Guardian alignment {'verified' if state.is_aligned else 'compromised'}"
        )
        
    async def scan_emotional_state(self):
        """Scan emotional firewall state"""
        state = await self.firewall.check_state()
        await self._speak(f"Emotional state: {state.status}")
        
    async def activate_protection(self):
        """Enter protected mode"""
        try:
            await self.guardian.enhance_protection()
            self.state = LaunchStates.PROTECTED
            await self._speak("Enhanced protection mode activated")
        except Exception as e:
            logger.error(f"Protection activation failed: {str(e)}")
            
    async def emergency_stop(self):
        """Emergency shutdown procedure"""
        try:
            await self._speak("Initiating emergency shutdown")
            self.state = LaunchStates.EMERGENCY
            # Close eye
            if self.eye:
                await self.eye.animate_close()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Emergency shutdown failed: {str(e)}")
            
    async def verify_memory(self):
        """Verify quantum memory anchor"""
        try:
            from astra.core.memory import get_memory
            memory = get_memory()
            state = await memory.verify_quantum_anchor()
            await self._speak(
                f"Memory anchor {'verified' if state else 'compromised'}"
            )
        except Exception as e:
            logger.error(f"Memory verification failed: {str(e)}")
            
    async def check_alignment(self):
        """Check sovereign alignment"""
        state = await self.guardian.verify_alignment()
        await self._speak(
            f"Sovereign alignment {'verified' if state.is_aligned else 'compromised'}"
        )
        
    async def run_security_scan(self) -> None:
        """Run full security scan"""
        try:
            self._log_message("Initiating security scan...")
            
            # Verify integrity
            integrity_ok = self.security.integrity.verify_integrity()
            
            # Check device state
            device_ok = await self._check_device_state()
            
            # Update GUI
            self._update_status(
                "Security scan complete",
                "green" if integrity_ok and device_ok else "red"
            )
            
            # Report results
            if integrity_ok and device_ok:
                await self._speak("Security scan complete. All systems secure.")
            else:
                await self._speak(
                    "Warning: Security scan detected potential issues."
                )
                
        except Exception as e:
            logger.error(f"Security scan failed: {str(e)}")
            await self._speak("Security scan failed")
            
    async def verify_integrity(self) -> None:
        """Verify system integrity"""
        try:
            self._log_message("Verifying system integrity...")
            
            if self.security.integrity.verify_integrity():
                await self._speak("System integrity verified")
            else:
                await self._speak("Warning: System integrity check failed")
                
        except Exception as e:
            logger.error(f"Integrity check failed: {str(e)}")
            await self._speak("Integrity verification failed")
            
    async def _check_device_state(self) -> bool:
        """Check device state"""
        try:
            # Get system metrics
            import psutil
            
            # Check CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                logger.warning(f"High CPU usage: {cpu_percent}%")
                return False
                
            # Check memory
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                logger.warning(f"High memory usage: {memory.percent}%")
                return False
                
            # Check disk
            disk = psutil.disk_usage('.')
            if disk.percent > 90:
                logger.warning(f"Low disk space: {disk.free} bytes free")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Device state check failed: {str(e)}")
            return False
        
    async def launch(self, gui: bool = True) -> None:
        """Launch ASTRA with optional GUI"""
        mode = "gui" if gui else "headless"
        timer = self.prime_metrics.start_activation_timer(mode)
        
        try:
            # Create logs directory
            Path("logs").mkdir(exist_ok=True)
            
            # Set process priority
            pid = win32api.GetCurrentProcessId()
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
            win32process.SetPriorityClass(handle, win32process.HIGH_PRIORITY_CLASS)
            
            # Log prime request sequence
            logger.info("Initiating PRIME REQUEST sequence")
            prime_sequence = self.prime_manager.get_activation_sequence()
            logger.info(prime_sequence)
            
            # Execute prime request with metrics
            self.prime_manager.log_activation({
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "process_id": self.process_id
            })
            
            # Record activation in metrics
            self.prime_metrics.record_activation(mode)
            
            # Start system initialization
            await self._initialize_core_systems()
            
            if gui:
                await self._launch_with_gui()
            else:
                await self._launch_headless()
            
            # Stop activation timer
            timer.observe()
            
        except Exception as e:
            logger.error(f"Launch failed: {str(e)}")
            self.prime_metrics.record_activation(mode, status="failed")
            if gui and self.root:
                self.root.destroy()
            sys.exit(1)
            
    async def _launch_with_gui(self) -> None:
        """Launch with GUI overlay"""
        # Create GUI
        self.root = tk.Tk()
        self.root.title("ASTRA 2.0 Launch Control")
        self.root.geometry("600x400")
        self._setup_gui()
        
        # Get window handle
        self._window_hwnd = win32gui.GetParent(self.root.winfo_id())
        
        # Start startup in background
        self._startup_task = asyncio.create_task(self._run_startup())
        
        # Run GUI
        while True:
            self.root.update()
            await asyncio.sleep(0.1)
            
            if self._startup_task and self._startup_task.done():
                if self._startup_task.exception():
                    self._update_status("Launch failed", "red")
                    self._log_message("ERROR: Startup failed")
                    await asyncio.sleep(5)
                    self.root.destroy()
                    sys.exit(1)
                break
                
        self._update_status("ASTRA Online", "green")
        self._log_message("Startup complete - ASTRA is sovereign")
            
    def _setup_gui(self) -> None:
        """Setup GUI components"""
        # Configure window
        self.root.configure(bg='black')
        style = ttk.Style()
        style.configure('TLabel', background='black', foreground='green')
        style.configure('TLabelframe', background='black', foreground='green')
        style.configure('TCheckbutton', background='black', foreground='green')
        
        # ASTRA Eye
        self.eye = AstraEye(self.root, width=150, height=150, bg='black')
        self.eye.pack(pady=10)
        
        # Control Panel Frame
        control_frame = ttk.LabelFrame(self.root, text="Control Panel")
        control_frame.pack(padx=10, pady=5, fill="x")
        
        # Online/Offline toggle
        self.online_var = tk.BooleanVar(value=True)
        online_cb = ttk.Checkbutton(
            control_frame,
            text="Online Mode",
            variable=self.online_var,
            command=self._toggle_online_mode
        )
        online_cb.pack(side="left", padx=5)
        
        # Voice Interface toggle
        self.voice_var = tk.BooleanVar(value=True)
        voice_cb = ttk.Checkbutton(
            control_frame,
            text="Voice Interface",
            variable=self.voice_var,
            command=self._toggle_voice_interface
        )
        voice_cb.pack(side="left", padx=5)
        
        # Mission Profile selector
        if self.mission_profiles:
            profile_frame = ttk.Frame(control_frame)
            profile_frame.pack(side="right", padx=5)
            
            ttk.Label(profile_frame, text="Mission:").pack(side="left")
            self.profile_var = tk.StringVar()
            profile_menu = ttk.OptionMenu(
                profile_frame,
                self.profile_var,
                "default",
                *self.mission_profiles.keys()
            )
            profile_menu.pack(side="left", padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(self.root, text="Launch Status")
        status_frame.pack(padx=10, pady=5, fill="x")
        
        self.status_var = tk.StringVar(value="Initializing...")
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            font=("Consolas", 12, "bold")
        )
        status_label.pack(pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        progress = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100
        )
        progress.pack(fill="x", padx=5, pady=5)
        
        # Logs frame
        logs_frame = ttk.LabelFrame(self.root, text="Launch Logs")
        logs_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        self.logs_text = tk.Text(
            logs_frame,
            height=10,
            font=("Consolas", 10),
            bg="black",
            fg="green"
        )
        self.logs_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Timestamp the start
        self._log_message("ASTRA Launch Control initialized")
        
    def _update_status(self, status: str, color: str = "green") -> None:
        """Update status display"""
        if self.status_var:
            self.status_var.set(status)
            
    def _update_progress(self, value: float) -> None:
        """Update progress bar"""
        if self.progress_var:
            self.progress_var.set(value)
            
    def _log_message(self, message: str) -> None:
        """Add message to log display"""
        if self.logs_text:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.logs_text.insert("end", f"[{timestamp}] {message}\n")
            self.logs_text.see("end")
            
    async def _launch_headless(self) -> None:
        """Launch without GUI"""
        logger.info("Starting ASTRA in headless mode...")
        await self._run_startup()
        logger.info("ASTRA startup complete")
        
    async def _initialize_core_systems(self) -> None:
        """Initialize and verify all core ASTRA systems"""
        core_systems = {
            'neural_engine': self._init_neural_engine,
            'memory_core': self._init_memory_core,
            'guardian_firewall': self._init_guardian,
            'voice_input': self._init_voice,
            'vision_integration': self._init_vision,
            'task_engine': self._init_task_engine,
            'interface': self._init_interface,
            'alignment_check': self._verify_alignment
        }
        
        for system, init_func in core_systems.items():
            try:
                await init_func()
                self.prime_metrics.update_system_readiness(system, True)
                logger.info(f"{system} initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize {system}: {str(e)}")
                self.prime_metrics.update_system_readiness(system, False)
                raise
    
    async def _run_startup(self) -> None:
        """Execute startup sequence"""
        try:
            # Verify system integrity
            self._update_status("Verifying system integrity")
            self._log_message("Running integrity checks...")
            if not self.security.integrity.verify_integrity():
                raise Exception("System integrity check failed")
                
            # Check power state
            self._update_status("Checking power state")
            self._log_message("Verifying power conditions...")
            if not self.power_state.update():
                raise Exception("System power state unsuitable for startup")
                
            # Import here to prevent circular imports
            from astra.core.startup.startup import SovereignStartup
            startup = SovereignStartup()
            
            # Check power state
            self._update_status("Checking power state")
            if not self.power_state.update():
                raise Exception("System power state unsuitable for startup")
            
            # Start eye animation
            if self.eye:
                await self.eye.animate_open()
            
            # Pre-initialization
            self.state = LaunchStates.AWAKENING
            self._update_status("Pre-initialization checks")
            self._update_progress(10)
            self._log_message("Running system checks...")
            
            # Speak greeting if enabled
            if self.greeting_enabled and self.tts_engine:
                greeting = (
                    "ASTRA initialization sequence activated. "
                    "Sovereign protocols engaged. "
                    "Divine alignment verified."
                )
                await self._speak(greeting)
                
            # Start post-boot command processor
            if self.voice_interface_enabled:
                await self.command_processor.start_listening()
                self._log_message("Post-boot command interface active")
                
    async def shutdown(self) -> None:
        """Clean shutdown procedure"""
        try:
            # Stop command processor
            if self.voice_interface_enabled:
                await self.command_processor.stop_listening()
                
            # Close eye animation
            if self.eye:
                await self.eye.animate_close()
                
            # Final status
            await self._speak("ASTRA shutting down. Sovereign protocols preserved.")
            
            # Clean exit
            if self.root:
                self.root.destroy()
            sys.exit(0)
                
        except Exception as e:
            logger.error(f"Shutdown failed: {str(e)}")
            sys.exit(1)
            
            # Initialize startup system
            self._update_status("Loading core systems")
            self._update_progress(30)
            self._log_message("Initializing core systems...")
            
            # Start startup sequence
            self._update_status("Starting sovereign startup")
            self._update_progress(50)
            if not await startup.initialize():
                raise Exception("Startup initialization failed")
                
            # Wait for voice activation
            self._update_status("Waiting for voice activation")
            self._update_progress(70)
            self._log_message("Listening for wake words...")
            
            # Core warmup
            self._update_status("Warming up neural core")
            self._update_progress(90)
            self._log_message("Neural warmup sequence initiated...")
            
            # Complete
            self.state = LaunchStates.SOVEREIGN
            self._update_status("ASTRA Online")
            self._update_progress(100)
            self._log_message("ASTRA is sovereign and ready")
            
        except Exception as e:
            self.state = LaunchStates.EMERGENCY
            logger.error(f"Startup failed: {str(e)}")
            
            # Close eye on failure
            if self.eye:
                await self.eye.animate_close()
                
            raise
            
    def _protect_core_paths(self) -> None:
        """Protect core system paths"""
        try:
            core_paths = [
                Path("astra-2.0/core"),
                Path("astra-2.0/security"),
                Path("models"),
                Path("config"),
                Path("launch_astra.py")
            ]
            
            for path in core_paths:
                if path.exists():
                    self.security.protect_core_path(str(path.resolve()))
                    
        except Exception as e:
            logger.error(f"Failed to protect core paths: {str(e)}")
            
    async def activate_immunity(self) -> bool:
        """Activate full system immunity"""
        try:
            self._log_message("Activating immunity protocol...")
            
            # Verify creator first
            if not await self._verify_creator_command():
                return False
                
            # Activate immunity
            if not await self.security.activate_immunity():
                self._log_message("Immunity activation failed")
                return False
                
            self._log_message("Immunity protocol active")
            await self._speak("Immunity protocol activated. All systems protected.")
            return True
            
        except Exception as e:
            logger.error(f"Immunity activation failed: {str(e)}")
            return False
            
    async def _verify_creator_command(self) -> bool:
        """Verify creator for sensitive commands"""
        try:
            # Record audio
            audio = await self._record_audio(duration=3.0)
            
            # Get biometric system
            from astra.core.security.biometric import get_biometric
            biometric = get_biometric()
            
            # Verify voice
            is_verified, confidence = await biometric.verify_voice(audio)
            
            if not is_verified:
                await self._speak("Creator verification failed")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Creator verification failed: {str(e)}")
            return False
            
    def _load_mission_profiles(self) -> dict:
        """Load available mission profiles"""
        try:
            profile_path = Path("config/mission_profiles.json")
            if profile_path.exists():
                with open(profile_path) as f:
                    return json.load(f)
            return {"default": {"name": "Default Profile", "settings": {}}}
        except Exception as e:
            logger.error(f"Failed to load mission profiles: {str(e)}")
            return {}
            
    def _toggle_online_mode(self) -> None:
        """Toggle online/offline mode"""
        self.online_mode = self.online_var.get()
        mode = "online" if self.online_mode else "offline"
        self._log_message(f"Switched to {mode} mode")
        
    def _toggle_voice_interface(self) -> None:
        """Toggle voice interface"""
        self.voice_interface_enabled = self.voice_var.get()
        state = "enabled" if self.voice_interface_enabled else "disabled"
        self._log_message(f"Voice interface {state}")
        
    async def _speak(self, text: str) -> None:
        """Speak text using TTS"""
        if self.greeting_enabled and self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS failed: {str(e)}")
                
async def main():
    """Main entry point"""
    launcher = AstraLauncher()
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="ASTRA 2.0 Launch Control")
    parser.add_argument("--no-gui", action="store_true", help="Run in headless mode")
    parser.add_argument("--offline", action="store_true", help="Start in offline mode")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice interface")
    parser.add_argument("--no-greeting", action="store_true", help="Disable ASTRA greeting")
    parser.add_argument("--mission", help="Load specific mission profile")
    args = parser.parse_args()
    
    # Configure launcher
    launcher.online_mode = not args.offline
    launcher.voice_interface_enabled = not args.no_voice
    launcher.greeting_enabled = not args.no_greeting
    if args.mission:
        launcher.mission_profile = args.mission
    
    # Launch ASTRA
    await launcher.launch(gui=not args.no_gui)
    
if __name__ == "__main__":
    try:
        if os.name == "nt":  # Windows
            # Use Windows event loop
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy()
            )
            
        # Run main
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Launch terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Launch failed: {str(e)}")
        sys.exit(1)

class AstraLauncher:
    """Windows 11 launcher for ASTRA"""
    
    def __init__(self):
        self.state = LaunchStates.INITIALIZING
        self.startup = None
        self.guardian = None
        self.launch_time = datetime.now()
        self.process_id = os.getpid()
        
        # Initialize prime request manager
        from astra.core.activation.prime_request import PrimeRequestManager
        from astra.core.metrics.prime_metrics import PrimeRequestMetrics
        from prometheus_client import CollectorRegistry
        
        self.registry = CollectorRegistry()
        self.prime_manager = PrimeRequestManager()
        self.prime_metrics = PrimeRequestMetrics(registry=self.registry)
    
def main():
    """Main launcher entry point"""
    try:
        logger.info("Starting ASTRA 2.0 Launcher")
        
        # Setup environment
        setup_environment()
        
        # Import ASTRA modules
        from astra.core.startup import get_startup
        from astra.core.sovereign.guardian import get_guardian
        
        # Initialize startup system
        startup = get_startup()
        
        # Initialize guardian
        guardian = get_guardian()
        
        logger.info("ASTRA systems initialized")
        logger.info("Listening for voice activation...")
        
        # Keep main thread alive
        try:
            while True:
                status = startup.get_startup_status()
                if status["state"] == "sovereign":
                    guardian_status = guardian.get_guardian_status()
                    logger.info(f"Guardian State: {guardian_status['guardian_state']}")
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Shutting down ASTRA...")
            startup.stop_listening()
            
    except Exception as e:
        logger.error(f"Launch failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
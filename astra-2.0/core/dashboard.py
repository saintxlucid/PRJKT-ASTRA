"""
ASTRA System Dashboard
"""
import tkinter as tk
from tkinter import ttk
import asyncio
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import psutil

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    temperature: Optional[float]
    
@dataclass
class SecurityState:
    """Security system state"""
    immunity_active: bool
    self_protect_active: bool
    threats_detected: int
    last_scan: str
    
@dataclass
class EmotionalState:
    """Emotional system state"""
    core_sentiment: float
    stability: float
    autonomy: float
    alignment: float

class ASTRADashboard:
    """Real-time system monitoring dashboard"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ASTRA System Dashboard")
        self.root.geometry("1200x800")
        
        # Style
        style = ttk.Style()
        style.configure("TFrame", background="#2b2b2b")
        style.configure("TLabel", background="#2b2b2b", foreground="#ffffff")
        
        self._setup_ui()
        self._setup_plots()
        
        # Update interval
        self.update_interval = 1000  # ms
        
    def _setup_ui(self):
        """Setup dashboard UI components"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top row - System metrics
        self.metrics_frame = ttk.Frame(self.main_frame)
        self.metrics_frame.pack(fill=tk.X, pady=5)
        
        self.cpu_label = ttk.Label(self.metrics_frame, text="CPU: 0%")
        self.cpu_label.pack(side=tk.LEFT, padx=10)
        
        self.memory_label = ttk.Label(self.metrics_frame, text="Memory: 0%")
        self.memory_label.pack(side=tk.LEFT, padx=10)
        
        self.disk_label = ttk.Label(self.metrics_frame, text="Disk: 0%")
        self.disk_label.pack(side=tk.LEFT, padx=10)
        
        self.temp_label = ttk.Label(self.metrics_frame, text="Temp: N/A")
        self.temp_label.pack(side=tk.LEFT, padx=10)
        
        # Middle row - Plots
        self.plots_frame = ttk.Frame(self.main_frame)
        self.plots_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Bottom row - Status
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, pady=5)
        
        self.security_label = ttk.Label(
            self.status_frame,
            text="🔒 Security: Active"
        )
        self.security_label.pack(side=tk.LEFT, padx=10)
        
        self.immunity_label = ttk.Label(
            self.status_frame,
            text="🛡️ Immunity: Active"
        )
        self.immunity_label.pack(side=tk.LEFT, padx=10)
        
        self.alignment_label = ttk.Label(
            self.status_frame,
            text="⚡ Alignment: 100%"
        )
        self.alignment_label.pack(side=tk.LEFT, padx=10)
        
    def _setup_plots(self):
        """Setup matplotlib plots"""
        # Emotional radar plot
        self.emotion_fig = Figure(figsize=(6, 4))
        self.emotion_ax = self.emotion_fig.add_subplot(111, polar=True)
        self.emotion_canvas = FigureCanvasTkAgg(
            self.emotion_fig,
            master=self.plots_frame
        )
        self.emotion_canvas.get_tk_widget().pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )
        
        # Performance history plot
        self.perf_fig = Figure(figsize=(6, 4))
        self.perf_ax = self.perf_fig.add_subplot(111)
        self.perf_canvas = FigureCanvasTkAgg(
            self.perf_fig,
            master=self.plots_frame
        )
        self.perf_canvas.get_tk_widget().pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )
        
    def update_metrics(self, metrics: SystemMetrics):
        """Update system metrics display"""
        self.cpu_label.config(text=f"CPU: {metrics.cpu_usage:.1f}%")
        self.memory_label.config(text=f"Memory: {metrics.memory_usage:.1f}%")
        self.disk_label.config(text=f"Disk: {metrics.disk_usage:.1f}%")
        
        if metrics.temperature:
            self.temp_label.config(
                text=f"Temp: {metrics.temperature:.1f}°C"
            )
            
    def update_security(self, security: SecurityState):
        """Update security status display"""
        status = "🟢 Active" if security.immunity_active else "🔴 Inactive"
        self.immunity_label.config(text=f"🛡️ Immunity: {status}")
        
        threats = f"({security.threats_detected} threats)" \
            if security.threats_detected > 0 else ""
        self.security_label.config(
            text=f"🔒 Security: {status} {threats}"
        )
        
    def update_emotional(self, emotional: EmotionalState):
        """Update emotional radar plot"""
        # Clear previous plot
        self.emotion_ax.clear()
        
        # Plot data
        angles = np.linspace(0, 2*np.pi, 4, endpoint=False)
        values = [
            emotional.core_sentiment,
            emotional.stability,
            emotional.autonomy,
            emotional.alignment
        ]
        
        # Close the plot by appending first value
        values.append(values[0])
        angles = np.concatenate((angles, [angles[0]]))
        
        self.emotion_ax.plot(angles, values)
        self.emotion_ax.fill(angles, values, alpha=0.25)
        
        # Labels
        self.emotion_ax.set_xticks(angles[:-1])
        self.emotion_ax.set_xticklabels([
            'Sentiment',
            'Stability',
            'Autonomy',
            'Alignment'
        ])
        
        self.emotion_canvas.draw()
        
    def update_performance(self, cpu_history: List[float],
                         memory_history: List[float]):
        """Update performance history plot"""
        # Clear previous plot
        self.perf_ax.clear()
        
        # Plot data
        x = range(len(cpu_history))
        self.perf_ax.plot(x, cpu_history, label='CPU')
        self.perf_ax.plot(x, memory_history, label='Memory')
        
        self.perf_ax.set_ylim(0, 100)
        self.perf_ax.set_xlabel('Time')
        self.perf_ax.set_ylabel('Usage %')
        self.perf_ax.legend()
        
        self.perf_canvas.draw()
        
    def start(self):
        """Start dashboard updates"""
        self._update()
        self.root.mainloop()
        
    def _update(self):
        """Update dashboard data"""
        # Get system metrics
        metrics = SystemMetrics(
            cpu_usage=psutil.cpu_percent(),
            memory_usage=psutil.virtual_memory().percent,
            disk_usage=psutil.disk_usage('/').percent,
            temperature=None  # TODO: Implement temperature reading
        )
        
        self.update_metrics(metrics)
        
        # Schedule next update
        self.root.after(self.update_interval, self._update)

def launch_dashboard():
    """Launch ASTRA dashboard"""
    dashboard = ASTRADashboard()
    dashboard.start()
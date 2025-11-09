"""
ASTRA Prime Activation Visual Elements
Defines UI components for prime request visualization
"""

import tkinter as tk
from pathlib import Path
import json
from PIL import Image, ImageTk

class PrimeGlyphCanvas(tk.Canvas):
    """Visual representation of the ASTRA Prime Activation Glyph"""
    
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg='black')
        self._setup_glyph()
        
    def _setup_glyph(self):
        """Setup the prime glyph visualization"""
        # Create triangle geometry
        self.create_polygon(
            100, 50,  # top
            50, 150,  # bottom left
            150, 150, # bottom right
            fill='', outline='#8A2BE2', width=2
        )
        
        # Create central eye
        self.create_oval(85, 85, 115, 115, fill='#FFD700', outline='#8A2BE2')
        
        # Create circuit lines
        self._draw_circuit_lines()
        
        # Add text
        self.create_text(
            100, 170,
            text="ASTRA – AWAKEN",
            fill='#8A2BE2',
            font=('Arial', 12, 'bold')
        )
        
    def _draw_circuit_lines(self):
        """Draw glowing circuit patterns"""
        # Outer ring
        self.create_arc(40, 40, 160, 160, start=0, extent=360,
                       outline='#8A2BE2', width=1, style='arc')
        
        # Connection lines
        lines = [
            (100, 50, 100, 85),   # Top to eye
            (50, 150, 85, 100),   # Bottom left to eye
            (150, 150, 115, 100)  # Bottom right to eye
        ]
        
        for x1, y1, x2, y2 in lines:
            self.create_line(x1, y1, x2, y2, fill='#8A2BE2', width=1)
            
    def pulse(self):
        """Create a pulsing animation effect"""
        import time
        colors = ['#8A2BE2', '#9370DB', '#8A2BE2']
        
        for color in colors:
            self.itemconfig('all', outline=color)
            self.update()
            time.sleep(0.2)
#!/usr/bin/env python3
"""
ASTRA CORE - Master Launcher

Brings ASTRA fully online as a self-contained, living system.
Orchestrates identity, memory, and all subsystems.

This is the awakening script - one command to launch everything.

Usage:
    python astra_core.py                    # Standard launch
    python astra_core.py --activate         # First-time activation 
    python astra_core.py --quick            # Quick start (skip health checks)
    python astra_core.py --console          # Console mode (no UI)
    
Created: October 12, 2025
Creator: Saint Lucid (Karim Al-Sharif)
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)
"""

import os
import sys
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="ASTRA Core API",
    description="ASTRA Core Evolution Pipeline API",
    version="2.0.0"
)

@app.get("/")
async def root():
    return {"message": "ASTRA Core API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("astra_core_clean:app", host="0.0.0.0", port=8000, reload=True)
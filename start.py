#!/usr/bin/env python3
"""Simple ASTRA launcher - bypasses path issues"""
import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

# Set environment
import os
os.environ["ASTRA_LLM_PROVIDER"] = "openai_compatible"
os.environ["OPENAI_BASE_URL"] = "http://localhost:9010/v1"
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["ASTRA_LLM_MODEL_NAME"] = "gpt-oss-20b"
os.environ["DATABASE_URL"] = "postgresql://astra:astra@localhost:5432/astra"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_SECRET"] = "dev-secret-key"

print("🌌 Starting ASTRA Master...")
print(f"Model: {os.environ['ASTRA_LLM_MODEL_NAME']}")
print(f"Endpoint: {os.environ['OPENAI_BASE_URL']}")
print("="*70)

# Import and run
import uvicorn
uvicorn.run(
    "astra_master:app",
    host="0.0.0.0",
    port=8000,
    reload=False,
    log_level="info"
)

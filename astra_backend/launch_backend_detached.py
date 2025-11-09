import subprocess
import os
import sys

# Set environment variable
os.environ["ASTRA_EMBEDDINGS_MODEL"] = "sentence-transformers/all-MiniLM-L6-v2"

# Launch uvicorn as detached process
python_exe = r"X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\.venv\Scripts\python.exe"
backend_dir = r"X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra_backend"

proc = subprocess.Popen(
    [python_exe, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=backend_dir,
    creationflags=subprocess.CREATE_NEW_CONSOLE,
    env=os.environ.copy()
)

print(f"Backend launched with PID: {proc.pid}")
print("Server should be starting at http://localhost:8000")

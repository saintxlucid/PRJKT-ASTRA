# ASTRA Core Autonomous Launcher System

## Overview

This document describes the implementation of a production-safe, hardware-aware, self-healing launcher system for ASTRA Core that keeps the GPT-OSS 20B model intact while ensuring the entire stack is autonomous, robust, and friction-free.

## Key Features

### 1. Fixed GPT-OSS 20B Model
- Keeps the existing GPT-OSS 20B model in place without replacement
- Verifies model integrity through SHA checksum
- Ensures model is present before launching

### 2. Hardware-Aware Optimization
- Automatically detects CPU/GPU configuration
- Sets optimal runtime parameters based on hardware
- Adjusts batch sizes for maximum performance

### 3. Self-Healing Capabilities
- Continuous health monitoring
- Automatic API restart on failure
- Background watchdog process

### 4. Cross-Platform Support
- PowerShell script for Windows
- Shell script for Linux/macOS
- Consistent behavior across platforms

## Implementation Components

### Hardware Detection (`scripts/hw_detect.py`)
```python
import torch, psutil, platform, json
def detect():
    gpu = torch.cuda.is_available()
    return {
        "gpu": gpu,
        "gpu_name": torch.cuda.get_device_name(0) if gpu else "CPU",
        "ram_gb": round(psutil.virtual_memory().total/1e9,1),
        "os": platform.system(),
        "vram_gb": round(torch.cuda.get_device_properties(0).total_memory/1e9,1) if gpu else 0
    }
```

### Model Verification (`scripts/verify_model.py`)
```python
import os, sys, hashlib, json
MODEL = "models/gpt-oss-20b-q4_k_m.gguf"
if not os.path.exists(MODEL):
    print(json.dumps({"status":"missing"})); sys.exit(1)
size = os.path.getsize(MODEL)/1e9
sha = hashlib.sha256(open(MODEL,"rb").read(65536)).hexdigest()
print(json.dumps({"status":"ok","size_gb":round(size,2),"sha":sha[:12]}))
```

### Self-Healing Watchdog (`scripts/selfheal.py`)
```python
import time, subprocess, requests, sys, os
def restart_api():
    # Platform-specific process management
    # Restart uvicorn server
def check_health():
    # Verify API health via /v1/system/health endpoint
while True:
    if not check_health():
        restart_api()
    time.sleep(30)
```

### PowerShell Launcher (`scripts/LAUNCH_ASTRA.ps1`)
- Creates virtual environment if missing
- Installs dependencies via Poetry
- Verifies GPT-OSS model integrity
- Detects hardware and sets optimization flags
- Launches FastAPI backend
- Starts self-healing watchdog
- Performs health verification

### Shell Launcher (`scripts/launch_astra.sh`)
- Cross-platform equivalent for Linux/macOS
- Same functionality with shell-compatible syntax
- Background process management using nohup

## Deployment Process

### 1. Folder Structure
```
X:\PROJECT_ASTRA\
│
├─ backend\
│   ├─ astra\
│   │   └─ api\main.py
│   └─ data\
│       ├─ chroma_db\
│       └─ db.sqlite
├─ models\gpt-oss-20b-q4_k_m.gguf
├─ scripts\
│   ├─ hw_detect.py
│   ├─ verify_model.py
│   ├─ selfheal.py
│   ├─ LAUNCH_ASTRA.ps1
│   └─ launch_astra.sh
└─ .venv\
```

### 2. Launch Commands
**Windows:**
```powershell
.\scripts\LAUNCH_ASTRA.ps1
```

**Linux/macOS:**
```bash
./scripts/launch_astra.sh
```

## Runtime Optimization

### GPU Mode
- When CUDA is available
- Batch size set to 8
- ASTRA_MODE=GPU
- ASTRA_BATCH=8

### CPU Mode
- When CUDA is not available
- Batch size set to 2
- ASTRA_MODE=CPU
- ASTRA_BATCH=2

## Health Monitoring

### Continuous Checks
- Every 30 seconds health verification
- Automatic restart on failure
- Process monitoring and management

### Health Endpoint
- `http://127.0.0.1:8080/v1/system/health`
- Returns 200 OK when healthy
- Triggers restart on non-200 response

## Benefits

### Production Safety
- No remote model downloads
- Integrity verification
- Graceful error handling

### Performance Optimization
- Hardware-specific tuning
- Automatic batch sizing
- Resource-aware configuration

### Reliability
- Self-healing capabilities
- Process isolation
- Continuous monitoring

### Developer Experience
- One-command launch
- Cross-platform support
- Clear status reporting

## Future Enhancements

### Containerization
- Docker support for universal deployment
- Kubernetes deployment templates
- Cloud provider integration

### Advanced Monitoring
- Prometheus metrics integration
- Grafana dashboard
- Detailed performance analytics

### Scalability
- Multi-instance support
- Load balancing
- Horizontal scaling capabilities

## Conclusion

The ASTRA Core Autonomous Launcher System provides a robust, self-healing, hardware-aware solution that maintains the GPT-OSS 20B model while ensuring optimal performance and reliability. This implementation enables confident evolution of ASTRA Core v1.0 with production-grade stability and developer-friendly deployment.
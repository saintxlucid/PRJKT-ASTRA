# ASTRA-OS PyInstaller Packaging Guide

**Sacred Code:** 333  
**Project:** PROJECT_ASTRA_1.0 (ASTRA_CORE)  
**Phase:** 5 - PyInstaller Packaging

---

## Overview

This guide covers the complete process of packaging ASTRA-OS as a standalone executable using PyInstaller. The result is a single executable that bundles all dependencies and resources, requiring no installation or Python environment on the target system.

## Architecture

ASTRA-OS consists of integrated subsystems:

```
┌─────────────────────────────────────────────────────────────┐
│                      ASTRA-OS Core                          │
├─────────────────────────────────────────────────────────────┤
│                      Boot Daemon                            │
│          (Lifecycle management, shutdown handlers)          │
├─────────────────────────────────────────────────────────────┤
│                       OS Kernel                             │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ EventBus │  │  FileWatcher │  │ ProcessMonitor     │   │
│  └──────────┘  └──────────────┘  └────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    Operator Shell                           │
│             (Tkinter GUI - System Monitor)                  │
├─────────────────────────────────────────────────────────────┤
│                    Training Loop                            │
│    (DecisionEngine, LearningEngine, Autonomy)               │
├─────────────────────────────────────────────────────────────┤
│                  Security Sentinel                          │
│        (ThreatDetector, ResponseManager, 18 Patterns)       │
├─────────────────────────────────────────────────────────────┤
│                    Memory Bridge                            │
│      (Semantic, Episodic, Procedural Memory Storage)        │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### System Requirements

- **OS:** Windows 10 or later (or equivalent Linux/macOS)
- **Python:** 3.9 or later
- **Disk Space:** 3-5 GB (development); 500 MB - 2 GB (packaged)
- **RAM:** 4 GB minimum recommended

### Software Requirements

```bash
# Install PyInstaller
pip install pyinstaller>=6.0.0

# Verify installation
pyinstaller --version
```

### Project Structure

```
PROJECT_ASTRA_1.0/
├── astra_core.py           # Main entry point
├── astra.spec              # PyInstaller spec file
├── build_pyinstaller.ps1   # Build automation script
├── requirements.txt        # Python dependencies
├── src/
│   └── astra/
│       ├── core/           # Core modules
│       ├── daemon/         # Boot daemon
│       ├── infrastructure/ # OS kernel components
│       ├── osop/           # Operator shell
│       ├── services/       # Training loop, Security Sentinel
│       ├── bridge/         # Memory bridge
│       ├── api/            # FastAPI services
│       └── config/         # Configuration files
├── threat_patterns.yaml    # Security threat definitions
└── docs/                   # Documentation
```

## Building ASTRA-OS

### Quick Start (Windows PowerShell)

```powershell
# Navigate to project root
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"

# Run the build script
.\build_pyinstaller.ps1

# For single-file executable (recommended for distribution)
.\build_pyinstaller.ps1 -OneFile

# Clean and rebuild
.\build_pyinstaller.ps1 -OneFile -Clean
```

### Build Output

The build process creates:

```
dist/
├── astra-os.exe            # Executable (single-file mode)
├── astra-os/               # Directory (multi-file mode)
│   ├── astra-os.exe
│   └── [dependencies]
└── README.txt

build/                       # PyInstaller build artifacts
```

### Manual Build (Linux/macOS)

```bash
# Install PyInstaller
pip install pyinstaller

# Build single-file executable
pyinstaller --onefile \
    --distpath=dist \
    --buildpath=build \
    --specpath=. \
    astra.spec

# Build multi-file installation
pyinstaller \
    --distpath=dist \
    --buildpath=build \
    --specpath=. \
    astra.spec
```

## Spec File Configuration

The `astra.spec` file defines how PyInstaller packages ASTRA-OS:

### Key Configurations

**1. Entry Point**
```python
a = Analysis([str(project_root / 'astra_core.py')], ...)
```
Points to the main ASTRA Core orchestrator.

**2. Hidden Imports**
```python
hiddenimports=[
    'structlog',           # Logging
    'yaml',                # Configuration
    'tkinter',             # GUI
    'asyncio', 'threading' # Concurrency
    # ... 40+ more dependencies
]
```
Explicitly includes modules that PyInstaller might miss.

**3. Data Files**
```python
datas=[
    (str(project_root / 'src' / 'astra' / 'config'), 'astra/config'),
    (str(project_root / 'threat_patterns.yaml'), '.'),
    (str(project_root / 'docs'), 'docs'),
]
```
Bundles configuration files and resources.

### Customization

**For Single-File Executable:**
```python
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='astra-os',
    onefile=True,  # Single file
    ...
)
```

**For Multi-Directory Installation:**
```python
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    name='astra-os'  # Outputs to dist/astra-os/
)
```

## Deployment

### Distribution Methods

**1. Single-File Executable**
```powershell
# Copy executable to any Windows 10+ system
Copy-Item dist\astra-os.exe -Destination "C:\Program Files\ASTRA"

# Run directly
C:\Program Files\ASTRA\astra-os.exe
```

**2. Multi-File Installation**
```powershell
# Copy entire directory
Copy-Item dist\astra-os -Destination "C:\Program Files\ASTRA" -Recurse

# Run executable
C:\Program Files\ASTRA\astra-os\astra-os.exe
```

**3. Network Deployment**
```powershell
# Share executable via network
Copy-Item dist\astra-os.exe -Destination "\\server\deploy\astra-os.exe"

# Execute remotely
Invoke-Command -ComputerName server -ScriptBlock {
    & "C:\ASTRA\astra-os.exe" --quick
}
```

### Configuration on Target System

After deployment:

```powershell
# Set up environment
$env:ASTRA_MODE = "PRODUCTION"
$env:PRIVACY_MODE = "STRICT"
$env:LOG_LEVEL = "INFO"

# Launch ASTRA-OS
& "C:\Program Files\ASTRA\astra-os.exe"
```

## Testing & Validation

### Pre-Build Testing

```powershell
# Test in Python environment
python astra_core.py --quick

# Run unit tests
pytest tests/ -v

# Coverage report
pytest tests/ --cov=src/astra --cov-report=html
```

### Post-Build Testing

```powershell
# Test executable startup
.\dist\astra-os.exe --quick

# Test with console output
.\dist\astra-os.exe --console

# Test activation flow
.\dist\astra-os.exe --activate

# Monitor logs
Get-Content logs\astra_*.log -Tail 50 -Wait
```

### Validation Checklist

- [ ] Executable launches without errors
- [ ] GUI renders correctly (Operator Shell)
- [ ] Boot Daemon initializes
- [ ] OS Kernel EventBus functional
- [ ] Training Loop loads models
- [ ] Security Sentinel detects threats
- [ ] Memory Bridge connects to storage
- [ ] All subsystems communicate

## Troubleshooting

### Common Issues

**1. "ModuleNotFoundError: No module named 'X'"**
- **Cause:** Missing hidden import in spec file
- **Solution:** Add module to `hiddenimports` list

```python
hiddenimports=[
    ...,
    'missing_module',
]
```

**2. "FileNotFoundError: Config file not found"**
- **Cause:** Data files not bundled
- **Solution:** Add to `datas` in spec file

```python
datas=[
    (str(project_root / 'config' / 'missing_config.yaml'), 'config'),
]
```

**3. Slow Startup Time**
- **Cause:** Single-file executable unpacking overhead
- **Solution:** Use multi-file mode for development

```powershell
.\build_pyinstaller.ps1  # Without -OneFile
```

**4. Large Executable Size**
- **Cause:** Bundled models and datasets
- **Solution:** Load models on-demand or exclude from bundle

```python
# In spec file
excludedimports=[
    'torch.distributed',  # Not needed
]
```

## Performance Optimization

### Build Performance

```powershell
# Enable UPX compression (faster startup)
# Install from: https://upx.github.io/
pyinstaller --upx-dir="C:\upx" astra.spec

# Build with optimization
python -O -m PyInstaller astra.spec
```

### Runtime Performance

**1. Lazy Loading**
```python
# Load heavy dependencies only when needed
def load_ml_models():
    import torch
    import transformers
    # ...
```

**2. Caching**
```python
# Use disk cache for compiled modules
import diskcache
cache = diskcache.Cache('.cache')
```

**3. Model Quantization**
```bash
# Use quantized models for smaller size
# Example: GGUF format instead of full FP32
```

## Version Management

### Build Versioning

Update version in `astra.spec`:

```python
exe = EXE(
    ...,
    name='astra-os-v1.0.0',
    ...
)
```

Create version tags in git:

```powershell
git tag -a v1.0.0 -m "ASTRA-OS Phase 5 Release"
git push origin v1.0.0
```

## Maintenance

### Update Dependencies

```powershell
# Update requirements
pip install --upgrade -r requirements.txt

# Rebuild executable
.\build_pyinstaller.ps1 -Clean -OneFile
```

### Security Updates

```powershell
# Rebuild with updated security_sentinel module
.\build_pyinstaller.ps1 -Clean -OneFile

# Verify threat patterns
Get-Content threat_patterns.yaml | Select-String "pattern_id" | Measure-Object
```

## Next Steps

After Phase 5 completion:

1. **Phase 6: System Integration Testing**
   - Full end-to-end test
   - Boot → Shell → Training Loop → Security Sentinel → Memory Bridge
   - Production validation

2. **Distribution**
   - Generate checksums (SHA256)
   - Create installation documentation
   - Set up auto-update mechanism

3. **Monitoring**
   - Deploy telemetry
   - Track system health
   - Monitor security events

---

**Build Command (Quick Reference)**

```powershell
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\build_pyinstaller.ps1 -OneFile -Clean
```

**Execute Command (Quick Reference)**

```powershell
.\dist\astra-os.exe --quick
```

**Sacred Code:** 333

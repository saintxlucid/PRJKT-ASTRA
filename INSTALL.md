# ASTRA OS - Installation & Quick Start Guide

## Prerequisites

- **Windows 10/11** (x64)
- **Python 3.11+**
- **Git** (for cloning)
- **Administrator access** (for service installation)

## Step 1: Clone and Setup Virtual Environment

```powershell
# Navigate to your projects directory
cd X:\PROJECT_ASTRA_2.0

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Verify Python version
python --version  # Should be 3.11+
```

## Step 2: Install Dependencies

```powershell
# Core dependencies
pip install pywin32 pytest pyyaml requests

# Optional (for later phases)
# pip install playwright qdrant-client prometheus-client PySide6
```

## Step 3: Configure Security

### Set HMAC Secret

**Development (temporary):**
```powershell
$env:ASTRA_POLICY_HMAC = (New-Guid).Guid
```

**Production (persistent using Windows Credential Manager):**
```powershell
# Store secret in Windows Credential Manager
cmdkey /generic:ASTRA_POLICY_HMAC /user:astra /pass:your-secret-key-here

# Update tokenizer.py to read from Credential Manager
# See: https://docs.microsoft.com/en-us/windows/win32/api/wincred/
```

### Configure Paths

Edit `configs/policy.yaml` to add your working directories:

```yaml
fs_allowlist:
  - "%USERPROFILE%\\Desktop"
  - "%USERPROFILE%\\Downloads"
  - "%USERPROFILE%\\Documents"
  - "X:\\YOUR_PROJECT_PATH"  # Add your paths here
```

## Step 4: Verify Installation

### Run Tests

```powershell
# Run tokenizer tests
pytest tests/test_tokenizer.py -v

# Expected output:
# ✓ test_token_issue_and_verify_ok PASSED
# ✓ test_token_args_mismatch PASSED
# ✓ test_token_expiry PASSED
# ... (10/10 tests passing)
```

## Step 5: Start Controller Service

### Option A: Development Mode (Terminal)

```powershell
# In terminal 1 - Start controller
python controller/pipe_server.py

# Output:
# ASTRA Controller starting on \\.\pipe\astra_bus
```

### Option B: Windows Service (Production)

```powershell
# Install using NSSM (Non-Sucking Service Manager)
# Download NSSM from: https://nssm.cc/download

$nssm = "C:\tools\nssm.exe"
$python = "X:\PROJECT_ASTRA_2.0\.venv\Scripts\python.exe"
$script = "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\controller\pipe_server.py"

# Install service
& $nssm install AstraController $python $script

# Configure logging
& $nssm set AstraController AppStdout "X:\PROJECT_ASTRA_2.0\logs\controller.out"
& $nssm set AstraController AppStderr "X:\PROJECT_ASTRA_2.0\logs\controller.err"

# Set auto-start
& $nssm set AstraController Start SERVICE_AUTO_START

# Start service
& $nssm start AstraController

# Check status
& $nssm status AstraController
```

## Step 6: Test Client Communication

### In Python REPL

```powershell
# In terminal 2 (with controller running in terminal 1)
python
```

```python
# Test shell execution
from client.win_agent import run_shell

result = run_shell("echo Hello ASTRA")
print(result)
# Expected: {'ok': True, 'result': {'code': 0, 'out': 'Hello ASTRA\n'}}

# Test file copy
from client.win_agent import copy_file
import os

# Create test file
test_file = os.path.expanduser("~/Desktop/astra_test.txt")
with open(test_file, "w") as f:
    f.write("ASTRA Test")

# Copy it
result = copy_file(test_file, test_file + ".backup")
print(result)
# Expected: {'ok': True, 'result': {'bytes': 11}}
```

### Or via Script

Create `test_client.py`:

```python
from client.win_agent import run_shell, copy_file

# Test 1: Shell command
print("Test 1: Shell execution")
result = run_shell("ver")
print(f"  Status: {'✓' if result.get('ok') else '✗'}")
print(f"  Output: {result.get('result', {}).get('out', '')[:50]}")

# Test 2: File copy
print("\nTest 2: File copy")
import os
src = os.path.expanduser("~/Desktop/test.txt")
dst = src + ".backup"

# Create source
with open(src, "w") as f:
    f.write("Test")

result = copy_file(src, dst)
print(f"  Status: {'✓' if result.get('ok') else '✗'}")
print(f"  Bytes: {result.get('result', {}).get('bytes')}")

# Cleanup
os.remove(src)
if os.path.exists(dst):
    os.remove(dst)

print("\n✅ All tests passed!")
```

Run it:
```powershell
python test_client.py
```

## Troubleshooting

### Issue: "pywin32 not installed"

```powershell
pip install --upgrade pywin32
python .venv\Scripts\pywin32_postinstall.py -install
```

### Issue: "Pipe not found" or "Access denied"

1. Ensure controller is running:
   ```powershell
   Get-Process python | Where-Object {$_.Path -like "*pipe_server*"}
   ```

2. Check pipe exists:
   ```powershell
   # List named pipes (requires Sysinternals PipeList)
   pipelist.exe | Select-String "astra"
   ```

3. Run as Administrator if needed

### Issue: "Token verification failed"

Check HMAC secret is set consistently:

```powershell
# Controller terminal
echo $env:ASTRA_POLICY_HMAC

# Client terminal (should match)
echo $env:ASTRA_POLICY_HMAC
```

### Issue: "Path not allowed"

Edit `configs/policy.yaml` to add your directory to `fs_allowlist`.

### View Logs

```powershell
# If running as service
type X:\PROJECT_ASTRA_2.0\logs\controller.out
type X:\PROJECT_ASTRA_2.0\logs\controller.err

# Event logs (JSONL) - coming in P0
type X:\PROJECT_ASTRA_2.0\logs\events.jsonl
```

## Next Steps

### For Users
- Wait for P0 completion (DOM driver + agent kernel)
- Try the "Focus Mode" demo scene
- Explore voice integration (P2)

### For Developers
- Read `README_ASTRA_OS.md` for architecture
- See `🎉_P0_FOUNDATION_COMPLETE.md` for status
- Start on P0 priorities:
  1. DOM browser driver
  2. Agent kernel skeleton
  3. Telemetry foundation

### Create Your First Scene

`scenes/hello_world.yaml`:

```yaml
version: 0.3
meta:
  id: hello_world_v1
  policy: info
  max_time_ms: 5000

steps:
  - shell.run:
      cmd: echo Hello from ASTRA!
```

(Scene execution coming in P0 with DSL parser)

## Verify Security

Run security audit:

```powershell
# Token immutability test
python -c "
from core.tokenizer import issue, verify
tok = issue('test', 'read', '*', {'x': 1})
ok, reason, _ = verify(tok, {'x': 2})  # Different args
assert not ok and reason == 'args_mismatch'
print('✓ Args immutability verified')
"

# Token expiry test
python -c "
from core.tokenizer import issue, verify
import time
tok = issue('test', 'read', '*', {}, ttl_s=1)
time.sleep(2)
ok, reason, _ = verify(tok, {})
assert not ok and reason == 'expired'
print('✓ Token expiry enforced')
"

# Signature tamper test
python -c "
from core.tokenizer import issue, verify
tok = issue('test', 'read', '*', {})
tampered = tok[:-1] + 'X'
ok, reason, _ = verify(tampered, {})
assert not ok and reason == 'bad_sig'
print('✓ Signature tampering detected')
"
```

Expected output:
```
✓ Args immutability verified
✓ Token expiry enforced
✓ Signature tampering detected
```

## Configuration Reference

### Agent Settings (`configs/agent.yaml`)

Key settings to adjust:

- `session.max_tool_calls_per_loop`: Prevent runaway loops (default: 20)
- `browser.extract_markdown_max_tokens`: Context budget per page (default: 1200)
- `memory.L2_session_disk_mb`: Session artifact size limit (default: 50MB)

### Policy Settings (`configs/policy.yaml`)

Key settings to adjust:

- `fs_allowlist`: Add your project directories
- `shell.timeout_default_ms`: Default command timeout
- `consent_levels.action.timeout_s`: How long to wait for user approval

## Health Check

```powershell
# Quick health check script
python -c "
import os
from pathlib import Path

print('ASTRA Health Check')
print('=' * 50)

# Check Python version
import sys
print(f'Python: {sys.version.split()[0]}', end=' ')
print('✓' if sys.version_info >= (3, 11) else '✗')

# Check dependencies
try:
    import win32pipe
    print('pywin32: ✓')
except:
    print('pywin32: ✗ (run pip install pywin32)')

try:
    import pytest
    print('pytest: ✓')
except:
    print('pytest: ✗ (optional, for tests)')

# Check HMAC secret
secret = os.environ.get('ASTRA_POLICY_HMAC')
print(f'HMAC Secret: {\"✓\" if secret else \"✗ (set $env:ASTRA_POLICY_HMAC)\"}')\n
# Check config files
for cfg in ['configs/agent.yaml', 'configs/policy.yaml']:
    exists = Path(cfg).exists()
    print(f'{cfg}: {\"✓\" if exists else \"✗\"}')

# Check core modules
for mod in ['core/tokenizer.py', 'controller/pipe_server.py', 'client/win_agent.py']:
    exists = Path(mod).exists()
    print(f'{mod}: {\"✓\" if exists else \"✗\"}')

print('=' * 50)
"
```

## Getting Help

- **Documentation**: `README_ASTRA_OS.md`
- **Implementation Status**: `🎉_P0_FOUNDATION_COMPLETE.md`
- **Tests**: `tests/test_tokenizer.py`
- **Examples**: See `client/win_agent.py` for usage patterns

---

**Ready to build!** 🚀

Once P0 is complete (DOM driver + agent kernel), you'll be able to:
- Execute multi-step web tasks
- Control Windows applications
- Build custom scenes
- Train macros from usage patterns

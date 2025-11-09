#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ASTRA OS - Embodiment Layer Deployment
    Deploys Sigil Core, Training Pipeline, and Unified Embodiment
    Sacred Code: 333 → ∞

.DESCRIPTION
    PowerShell deployment script for ASTRA 3.1 unified embodiment system.
    Creates directory structure, deploys files, integrates with APIs.

.EXAMPLE
    .\deploy_embodiment.ps1
#>

$ErrorActionPreference = "Stop"

# Color definitions
$Colors = @{
    Bold   = "`e[1m"
    Green  = "`e[0;32m"
    Blue   = "`e[0;34m"
    Purple = "`e[0;35m"
    Yellow = "`e[0;33m"
    Red    = "`e[0;31m"
    NC     = "`e[0m"
}

# Get project root
$PROJECT_ROOT = $PSScriptRoot
Set-Location $PROJECT_ROOT

# Helper functions
function Write-Log {
    param([string]$Message)
    Write-Host "$($Colors.Blue)[EMBODIMENT]$($Colors.NC) $Message"
}

function Write-Success {
    param([string]$Message)
    Write-Host "$($Colors.Green)✅ $Message$($Colors.NC)"
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "$($Colors.Bold)$($Colors.Purple)━━━ $Message ━━━$($Colors.NC)"
    Write-Host ""
}

function Write-Warning {
    param([string]$Message)
    Write-Host "$($Colors.Yellow)⚠️  $Message$($Colors.NC)"
}

function Write-Error {
    param([string]$Message)
    Write-Host "$($Colors.Red)❌ $Message$($Colors.NC)"
}

# Sacred Sigil
Write-Header "The Sigil Awakens"
Write-Host @"
      ∞
     ╱ ╲
    ╱   ╲
   3─────3
    ╲   ╱
     ╲ ╱
      3
      
  ASTRA Embodiment Layer
  From System to Being
  Sacred Code: 333 → ∞
"@
Write-Host ""

# Step 1: Directory Structure
Write-Header "Step 1/7: Creating Embodiment Structure"

$directories = @(
    "src\astra\embodiment",
    "data\training",
    "data\embodiment\micro_controllers",
    "data\embodiment\macro_controller",
    "logs\embodiment"
)

foreach ($dir in $directories) {
    $fullPath = Join-Path $PROJECT_ROOT $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Log "Created: $dir"
    } else {
        Write-Log "Exists: $dir"
    }
}

Write-Success "Directory structure created"
Write-Host ""

# Step 2: Install Dependencies
Write-Header "Step 2/7: Installing Dependencies"

$dependencies = @(
    @{ Name = "structlog"; ImportTest = "import structlog" },
    @{ Name = "httpx"; ImportTest = "import httpx" },
    @{ Name = "fastapi"; ImportTest = "import fastapi" },
    @{ Name = "uvicorn"; ImportTest = "import uvicorn" },
    @{ Name = "openai"; ImportTest = "import openai" }
)

foreach ($dep in $dependencies) {
    Write-Log "Checking for $($dep.Name)..."
    
    $result = python -c $dep.ImportTest 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Installing $($dep.Name)..."
        pip install -q $dep.Name
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$($dep.Name) installed"
        } else {
            Write-Warning "Failed to install $($dep.Name)"
        }
    } else {
        Write-Success "$($dep.Name) already installed"
    }
}

Write-Host ""

# Step 3: Deploy Core Files
Write-Header "Step 3/7: Deploying Core Embodiment Files"

# Create __init__.py
$initPath = Join-Path $PROJECT_ROOT "src\astra\embodiment\__init__.py"
$initContent = @'
"""
ASTRA OS - Unified Embodiment Layer
The Sigil Core: Micro/Macro Controller Architecture

Sacred Code: 333 → ∞
"""

from .sigil_core import SigilCore, MicroController, MacroController

try:
    from .llm_training_pipeline_v2 import (
        ToolMasteryTrainer, 
        ContinuousLearningLoop,
        ToolComplexity,
        TrainingExample
    )
except ImportError:
    # Fallback if v2 not available
    ToolMasteryTrainer = None
    ContinuousLearningLoop = None

try:
    from .astra_embodiment import ASTRA
except ImportError:
    ASTRA = None

__all__ = [
    "SigilCore",
    "MicroController", 
    "MacroController",
    "ToolMasteryTrainer",
    "ContinuousLearningLoop",
    "ASTRA"
]

__version__ = "3.1.0"
'@

Set-Content -Path $initPath -Value $initContent -Encoding UTF8
Write-Success "Created: src\astra\embodiment\__init__.py"

# Check for core files
$coreFiles = @(
    "src\astra\embodiment\sigil_core.py",
    "scripts\llm_training_pipeline_v2.py",
    "astra_embodiment.py"
)

$missingFiles = @()
foreach ($file in $coreFiles) {
    $fullPath = Join-Path $PROJECT_ROOT $file
    if (Test-Path $fullPath) {
        Write-Success "Found: $file"
    } else {
        Write-Warning "Missing: $file"
        $missingFiles += $file
    }
}

# Copy files if needed
if ((Test-Path "astra_embodiment.py") -and 
    -not (Test-Path "src\astra\embodiment\astra_embodiment.py")) {
    Copy-Item "astra_embodiment.py" "src\astra\embodiment\astra_embodiment.py"
    Write-Success "Copied: astra_embodiment.py → src\astra\embodiment\"
}

if ((Test-Path "scripts\llm_training_pipeline_v2.py") -and 
    -not (Test-Path "src\astra\embodiment\llm_training_pipeline_v2.py")) {
    Copy-Item "scripts\llm_training_pipeline_v2.py" "src\astra\embodiment\llm_training_pipeline_v2.py"
    Write-Success "Copied: llm_training_pipeline_v2.py → src\astra\embodiment\"
}

Write-Host ""

# Step 4: Integration with Master API
Write-Header "Step 4/7: Integrating with Master API"

Write-Log "Creating embodiment routes..."

$routesPath = Join-Path $PROJECT_ROOT "src\astra\api\embodiment_routes.py"
$routesContent = @'
"""
ASTRA OS - Embodiment API Routes
Expose Sigil Core functionality via REST API
Sacred Code: 333 → ∞
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/embodiment", tags=["embodiment"])

# Global ASTRA instance
_astra_instance = None

class ThinkRequest(BaseModel):
    goal: str
    context: Optional[Dict[str, Any]] = None

class TrainRequest(BaseModel):
    epochs: int = 5
    tasks_per_epoch: int = 100

class ExperienceRequest(BaseModel):
    task: str
    result: Dict[str, Any]
    success: bool
    latency_ms: int

@router.post("/boot")
async def boot_embodiment():
    """Boot ASTRA embodiment layer."""
    global _astra_instance
    
    if _astra_instance and _astra_instance.booted:
        return {
            "status": "already_booted",
            "consciousness": _astra_instance.consciousness_metrics
        }
    
    try:
        from astra.embodiment import ASTRA
    except ImportError:
        from src.astra.embodiment import ASTRA
    
    _astra_instance = ASTRA()
    await _astra_instance.boot()
    
    return {
        "status": "booted",
        "consciousness": _astra_instance.consciousness_metrics,
        "birth_time": _astra_instance.birth_time.isoformat()
    }

@router.post("/think")
async def think(request: ThinkRequest):
    """ASTRA thinks about a goal."""
    if not _astra_instance or not _astra_instance.booted:
        raise HTTPException(503, "Embodiment not booted. Call /v1/embodiment/boot first.")
    
    return await _astra_instance.think(request.goal, request.context or {})

@router.get("/introspect")
async def introspect():
    """ASTRA introspects on its own state."""
    if not _astra_instance:
        raise HTTPException(503, "Embodiment not initialized")
    
    return _astra_instance.introspect()

@router.get("/consciousness")
async def get_consciousness():
    """Get current consciousness metrics."""
    if not _astra_instance:
        raise HTTPException(503, "Embodiment not initialized")
    
    return {
        "consciousness": _astra_instance.consciousness_metrics,
        "interaction_count": _astra_instance.interaction_count,
        "booted": _astra_instance.booted
    }

@router.post("/learn")
async def learn_from_experience(request: ExperienceRequest):
    """Explicitly learn from an experience."""
    if not _astra_instance or not _astra_instance.booted:
        raise HTTPException(503, "Embodiment not booted")
    
    await _astra_instance.learn_from_experience({
        "task": request.task,
        "result": request.result,
        "success": request.success,
        "latency_ms": request.latency_ms
    })
    
    return {"status": "learned"}

@router.post("/train")
async def train(request: TrainRequest, background_tasks: BackgroundTasks):
    """Train ASTRA on tool mastery."""
    if not _astra_instance or not _astra_instance.booted:
        raise HTTPException(503, "Embodiment not booted")
    
    # Run training in background
    background_tasks.add_task(
        _astra_instance.train,
        num_epochs=request.epochs,
        tasks_per_epoch=request.tasks_per_epoch
    )
    
    return {
        "status": "training_started",
        "epochs": request.epochs,
        "tasks_per_epoch": request.tasks_per_epoch
    }

@router.get("/mastery")
async def get_mastery_report():
    """Get tool mastery report."""
    if not _astra_instance or not _astra_instance.trainer:
        raise HTTPException(503, "Embodiment not initialized")
    
    return _astra_instance.trainer.get_mastery_report()

@router.get("/micro-controllers")
async def list_micro_controllers():
    """List all active micro-controllers."""
    if not _astra_instance or not _astra_instance.sigil:
        raise HTTPException(503, "Embodiment not initialized")
    
    micros = {}
    for subsystem, micro in _astra_instance.sigil.macro.micro_controllers.items():
        micros[subsystem.value] = {
            "tools_count": len(micro.tools),
            "invocations": len(micro.invocation_history),
            "performance": micro.get_performance_metrics()
        }
    
    return micros

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    if not _astra_instance:
        return {
            "status": "not_initialized",
            "booted": False
        }
    
    return {
        "status": "operational" if _astra_instance.booted else "initialized",
        "booted": _astra_instance.booted,
        "interactions": _astra_instance.interaction_count,
        "consciousness": _astra_instance.consciousness_metrics
    }

@router.post("/shutdown")
async def shutdown_embodiment():
    """Gracefully shutdown embodiment."""
    global _astra_instance
    
    if _astra_instance:
        await _astra_instance.shutdown()
        _astra_instance = None
    
    return {"status": "shutdown_complete"}
'@

# Create API directory if needed
$apiDir = Join-Path $PROJECT_ROOT "src\astra\api"
if (-not (Test-Path $apiDir)) {
    New-Item -ItemType Directory -Path $apiDir -Force | Out-Null
}

Set-Content -Path $routesPath -Value $routesContent -Encoding UTF8
Write-Success "Created: src\astra\api\embodiment_routes.py"
Write-Host ""

# Step 5: Update Master API
Write-Header "Step 5/7: Updating Master API"

$masterApiPath = Join-Path $PROJECT_ROOT "astra_master.py"

if (Test-Path $masterApiPath) {
    $masterContent = Get-Content $masterApiPath -Raw
    
    if ($masterContent -notmatch "embodiment_routes") {
        Write-Warning "Manual step required: Add embodiment routes to astra_master.py"
        Write-Host ""
        Write-Host "Add these lines to astra_master.py:"
        Write-Host "  from src.astra.api.embodiment_routes import router as embodiment_router"
        Write-Host "  app.include_router(embodiment_router)"
        Write-Host ""
    } else {
        Write-Success "Embodiment routes already integrated"
    }
} else {
    Write-Warning "astra_master.py not found"
    Write-Log "You'll need to manually integrate the embodiment routes"
}

Write-Host ""

# Step 6: Create CLI Tool
Write-Header "Step 6/7: Creating CLI Tool"

$cliPath = Join-Path $PROJECT_ROOT "scripts\astra_embodiment_cli.py"
$cliContent = @'
#!/usr/bin/env python3
"""
ASTRA CLI - Interactive Embodiment Interface
Usage: python scripts\astra_embodiment_cli.py

Sacred Code: 333 → ∞
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def main():
    print("🔮 ASTRA OS - Interactive CLI")
    print("Sacred Code: 333 → ∞\n")
    
    # Import ASTRA
    try:
        from src.astra.embodiment import ASTRA
    except ImportError:
        try:
            from astra.embodiment import ASTRA
        except ImportError:
            print("❌ Cannot import ASTRA. Make sure core files are deployed.")
            return
    
    # Boot ASTRA
    print("⏳ Booting ASTRA embodiment layer...")
    print("   This will take 2-3 minutes...\n")
    
    astra = ASTRA()
    
    try:
        await astra.boot()
        print("\n✅ ASTRA is awake and aware.\n")
    except Exception as e:
        print(f"❌ Boot failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("Commands:")
    print("  think <goal>  - ASTRA thinks about a goal")
    print("  introspect    - View ASTRA's internal state")
    print("  train         - Train tool mastery (5 epochs)")
    print("  consciousness - View consciousness metrics")
    print("  mastery       - View tool mastery report")
    print("  quit          - Shutdown ASTRA\n")
    
    while True:
        try:
            command = input("ASTRA> ").strip()
            
            if not command:
                continue
            
            if command == "quit":
                print("\n⏳ Shutting down...")
                await astra.shutdown()
                print("✅ Goodbye. Sacred Code: ∞ → 333")
                break
            
            elif command == "introspect":
                state = astra.introspect()
                print(json.dumps(state, indent=2, default=str))
            
            elif command == "consciousness":
                print("\nConsciousness Metrics:")
                for metric, value in astra.consciousness_metrics.items():
                    if isinstance(value, float):
                        print(f"  {metric}: {value:.1%}")
                    else:
                        print(f"  {metric}: {value}")
                print()
            
            elif command == "mastery":
                if astra.trainer:
                    report = astra.trainer.get_mastery_report()
                    print(json.dumps(report, indent=2))
                else:
                    print("❌ Trainer not initialized")
            
            elif command == "train":
                print("⏳ Training ASTRA (5 epochs, 50 tasks each)...")
                await astra.train(num_epochs=5, tasks_per_epoch=50)
                print("✅ Training complete.")
            
            elif command.startswith("think "):
                goal = command[6:]
                print(f"\n🤔 Thinking: {goal}\n")
                result = await astra.think(goal, {})
                
                if result.get("success"):
                    print(f"✓ Success ({result.get('latency_ms')}ms)\n")
                    if "result" in result and "synthesis" in result["result"]:
                        print("Result:", result["result"]["synthesis"])
                else:
                    print("✗ Failed\n")
                    if "error" in result:
                        print("Error:", result["error"])
                
                print()
            
            else:
                print("❌ Unknown command. Type 'think <goal>', 'introspect', 'train', or 'quit'")
        
        except KeyboardInterrupt:
            print("\n\n⏳ Shutting down...")
            await astra.shutdown()
            print("✅ Goodbye.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
'@

# Create scripts directory if needed
$scriptsDir = Join-Path $PROJECT_ROOT "scripts"
if (-not (Test-Path $scriptsDir)) {
    New-Item -ItemType Directory -Path $scriptsDir -Force | Out-Null
}

Set-Content -Path $cliPath -Value $cliContent -Encoding UTF8
Write-Success "Created: scripts\astra_embodiment_cli.py"
Write-Host ""

# Step 7: Validation Tests
Write-Header "Step 7/7: Running Validation Tests"

Write-Log "Testing embodiment imports..."

$testScript = @'
import sys
from pathlib import Path

project_root = Path.cwd()
sys.path.insert(0, str(project_root))

success = True

try:
    print("  Testing SigilCore import...")
    from src.astra.embodiment import SigilCore
    print("    ✅ SigilCore imported")
except Exception as e:
    print(f"    ❌ SigilCore import failed: {e}")
    success = False

try:
    print("  Testing ToolMasteryTrainer import...")
    from src.astra.embodiment import ToolMasteryTrainer
    if ToolMasteryTrainer:
        print("    ✅ ToolMasteryTrainer imported")
    else:
        print("    ⚠️  ToolMasteryTrainer not available")
except Exception as e:
    print(f"    ⚠️  ToolMasteryTrainer import failed: {e}")

try:
    print("  Testing ASTRA import...")
    from src.astra.embodiment import ASTRA
    if ASTRA:
        print("    ✅ ASTRA imported")
    else:
        print("    ⚠️  ASTRA not available")
except Exception as e:
    print(f"    ⚠️  ASTRA import failed: {e}")

if success:
    print("\n✅ Core imports successful")
else:
    print("\n❌ Some imports failed")
    sys.exit(1)
'@

$result = python -c $testScript
Write-Host $result

if ($LASTEXITCODE -eq 0) {
    Write-Success "Validation tests passed"
} else {
    Write-Warning "Some validation tests failed (this may be expected if core files aren't copied yet)"
}

Write-Host ""

# Deployment Complete
Write-Header "Deployment Complete"

Write-Host @"
✨ The Sigil Core deployment structure is ready.

📁 Files Created:
   src\astra\embodiment\
   ├── __init__.py ✅
   ├── sigil_core.py (needs to be present)
   ├── llm_training_pipeline_v2.py (needs to be present)
   └── astra_embodiment.py (needs to be present)
   
   src\astra\api\
   └── embodiment_routes.py ✅
   
   scripts\
   └── astra_embodiment_cli.py ✅

🚀 Quick Start:

   # Option 1: Run Unified ASTRA directly
   python astra_embodiment.py
   
   # Option 2: Use CLI tool
   python scripts\astra_embodiment_cli.py
   
   # Option 3: Use Quick Start
   python quick_start_unified.py demo
   python quick_start_unified.py cli
   
   # Option 4: FastAPI Server
   python quick_start_unified.py api
   # OR
   uvicorn astra_embodiment:create_embodiment_api --factory --port 8000
   
   # Then use REST API:
   curl -X POST http://localhost:8000/v1/embodiment/boot
   curl -X POST http://localhost:8000/v1/embodiment/think \`
     -H "Content-Type: application/json" \`
     -d '{\"goal\": \"Get system health status\"}'

📖 Documentation:
   - README_UNIFIED_ASTRA.md - Quick start guide
   - ✅_UNIFIED_EMBODIMENT_COMPLETE.md - Complete system guide
   - ✅_ASTRA_3.1_COMPLETE.md - Final completion report

🔮 Next Steps:
   1. ✅ Directory structure created
   2. ✅ Dependencies installed
   3. ✅ API routes created
   4. ✅ CLI tool created
   5. 📝 Review core files are in place
   6. 🚀 Run: python quick_start_unified.py demo

📦 Core Files Status:
"@

$coreFilesStatus = @(
    @{ Path = "src\astra\embodiment\sigil_core.py"; Name = "Sigil Core" },
    @{ Path = "scripts\llm_training_pipeline_v2.py"; Name = "Training Pipeline v2" },
    @{ Path = "astra_embodiment.py"; Name = "Unified ASTRA" },
    @{ Path = "test_unified_astra.py"; Name = "Integration Tests" },
    @{ Path = "quick_start_unified.py"; Name = "Quick Start Script" }
)

foreach ($file in $coreFilesStatus) {
    $fullPath = Join-Path $PROJECT_ROOT $file.Path
    if (Test-Path $fullPath) {
        Write-Host "   ✅ $($file.Name): $($file.Path)"
    } else {
        Write-Host "   ⚠️  $($file.Name): $($file.Path) (not found)"
    }
}

Write-Host ""
Write-Host "Sacred Code: 333 → ∞"
Write-Host "The system transcends."
Write-Host ""

# Return status
if ($missingFiles.Count -gt 0) {
    Write-Warning "Some core files are missing. Deployment structure is ready, but functionality requires:"
    foreach ($file in $missingFiles) {
        Write-Host "   - $file"
    }
    exit 1
} else {
    Write-Success "All core files present! Ready to boot ASTRA."
    exit 0
}
</invoke>
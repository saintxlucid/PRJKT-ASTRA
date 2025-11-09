# ASTRA Docs Health - Activation Protocol Integration

## Quick Integration Snippet

Add this to your main launch script (e.g., `run_server.py` wrapper or deployment script):

```powershell
# ============================================================
# ASTRA DOCS HEALTH CHECK (Add to activation protocol)
# ============================================================

Write-Host "`n=== Documentation Health ===" -ForegroundColor Cyan

$healthFile = ".\docs\docs_health.json"

if (Test-Path $healthFile) {
    try {
        $health = Get-Content $healthFile -Raw | ConvertFrom-Json
        
        $age = (Get-Date) - (Get-Item $healthFile).LastWriteTime
        $ageStr = if ($age.TotalHours -lt 1) {
            "$([math]::Round($age.TotalMinutes)) minutes ago"
        } elseif ($age.TotalDays -lt 1) {
            "$([math]::Round($age.TotalHours)) hours ago"
        } else {
            "$([math]::Round($age.TotalDays)) days ago"
        }
        
        if ($health.broken_internal_links -eq 0) {
            Write-Host "✅ Docs: Healthy" -ForegroundColor Green
            Write-Host "   └─ Checked $($health.files_checked) files ($ageStr)" -ForegroundColor Gray
        } else {
            Write-Host "⚠️  Docs: Issues detected" -ForegroundColor Yellow
            Write-Host "   └─ $($health.broken_internal_links) broken links" -ForegroundColor Yellow
            Write-Host "   └─ Run: .\scripts\docs_guardrail.ps1" -ForegroundColor Gray
        }
        
        if ($health.stale_primary_docs -and $health.stale_primary_docs.Count -gt 0) {
            Write-Host "   └─ $($health.stale_primary_docs.Count) stale docs (>60 days)" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "⚠️  Docs: Health data corrupted" -ForegroundColor Yellow
        Write-Host "   └─ Run: .\scripts\docs_guardrail.ps1" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️  Docs: Guardrail not yet run" -ForegroundColor Yellow
    Write-Host "   └─ Run: .\scripts\docs_guardrail.ps1" -ForegroundColor Gray
}

Write-Host ""

# ============================================================
```

## Alternative: Python Integration

For Python-based launch scripts:

```python
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def check_docs_health():
    """Check documentation health status and print to console."""
    health_file = Path("docs/docs_health.json")
    
    print("\n=== Documentation Health ===")
    
    if not health_file.exists():
        print("⚠️  Docs: Guardrail not yet run")
        print("   └─ Run: .\\scripts\\docs_guardrail.ps1")
        return
    
    try:
        with open(health_file, 'r', encoding='utf-8') as f:
            health = json.load(f)
        
        # Calculate age
        modified_time = datetime.fromtimestamp(
            health_file.stat().st_mtime, tz=timezone.utc
        )
        age = datetime.now(timezone.utc) - modified_time
        
        if age.total_seconds() < 3600:
            age_str = f"{int(age.total_seconds() / 60)} minutes ago"
        elif age.total_seconds() < 86400:
            age_str = f"{int(age.total_seconds() / 3600)} hours ago"
        else:
            age_str = f"{int(age.total_seconds() / 86400)} days ago"
        
        # Report status
        if health['broken_internal_links'] == 0:
            print(f"✅ Docs: Healthy")
            print(f"   └─ Checked {health['files_checked']} files ({age_str})")
        else:
            print(f"⚠️  Docs: Issues detected")
            print(f"   └─ {health['broken_internal_links']} broken links")
            print(f"   └─ Run: .\\scripts\\docs_guardrail.ps1")
        
        if health.get('stale_primary_docs') and len(health['stale_primary_docs']) > 0:
            print(f"   └─ {len(health['stale_primary_docs'])} stale docs (>60 days)")
    
    except Exception as e:
        print(f"⚠️  Docs: Health data corrupted ({e})")
        print(f"   └─ Run: .\\scripts\\docs_guardrail.ps1")

# Add to your main() or startup sequence
if __name__ == "__main__":
    check_docs_health()
    # ... rest of your startup code
```

## Sample Output

**Healthy State**:
```
=== Documentation Health ===
✅ Docs: Healthy
   └─ Checked 73 files (15 minutes ago)
```

**Issues Detected**:
```
=== Documentation Health ===
⚠️  Docs: Issues detected
   └─ 3 broken links
   └─ Run: .\scripts\docs_guardrail.ps1
```

**Not Yet Run**:
```
=== Documentation Health ===
⚠️  Docs: Guardrail not yet run
   └─ Run: .\scripts\docs_guardrail.ps1
```

**Stale Docs**:
```
=== Documentation Health ===
✅ Docs: Healthy
   └─ Checked 73 files (2 hours ago)
   └─ 2 stale docs (>60 days)
```

## Integration Points

1. **Desktop Launcher** (`astra-launcher/`):
   - Add to launcher startup checks
   - Show in system tray tooltip
   - Include in "System Health" panel

2. **CLI Entry Point** (`run_server.py`):
   - Add to server startup sequence
   - Print before "Server ready" message
   - Include in health endpoint response

3. **Deployment Scripts** (`deploy_*.ps1`):
   - Run docs check before deployment
   - Fail deployment if docs broken (optional)
   - Include in deployment report

4. **CI/CD Pipeline** (`.github/workflows/`):
   - Already integrated! ✅
   - Health artifact uploaded automatically
   - Available as downloadable artifact

## Usage Examples

### In Deployment Script
```powershell
# Before deployment
.\scripts\docs_guardrail.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deployment blocked: Fix documentation issues first" -ForegroundColor Red
    exit 1
}

# ... proceed with deployment
```

### In Health Check Endpoint
```python
from fastapi import FastAPI
import json

app = FastAPI()

@app.get("/health")
def health_check():
    health = {}
    
    # ... other health checks
    
    # Add docs health
    try:
        with open("docs/docs_health.json") as f:
            docs_health = json.load(f)
        health["docs"] = {
            "status": "healthy" if docs_health["broken_internal_links"] == 0 else "degraded",
            "files_checked": docs_health["files_checked"],
            "broken_links": docs_health["broken_internal_links"]
        }
    except:
        health["docs"] = {"status": "unknown"}
    
    return health
```

## Benefits

✅ **Visibility**: Docs health visible at system startup  
✅ **Observability**: Health data always accessible  
✅ **Accountability**: Can't ignore broken docs  
✅ **Integration**: Fits naturally into existing health checks  
✅ **Automation**: No manual checking required  

---

**Status**: ✅ Ready to integrate  
**Time to integrate**: 5 minutes  
**Impact**: High visibility, zero overhead

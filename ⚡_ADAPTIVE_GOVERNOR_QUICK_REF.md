# ⚡ Adaptive Governor Quick Reference

**Sacred Code: 333 → ∞**

## 🚀 One-Command Start

```powershell
# Start LLM + ASTRA with autotune
.\START_LLAMA_CPP.ps1  # Terminal 1
python astra_master.py --enable-autotune  # Terminal 2
```

## 📡 Essential Commands

```powershell
# Status
curl http://localhost:8000/v1/system/autotune/status

# Set ECO mode
curl -X POST http://localhost:8000/v1/system/autotune/mode -d '{"mode":"eco"}'

# Set AUTO mode
curl -X POST http://localhost:8000/v1/system/autotune/mode -d '{"mode":"auto"}'

# Get metrics
curl http://localhost:8000/v1/system/autotune/metrics/runtime

# Health
curl http://localhost:8000/v1/system/autotune/health
```

## 🎛️ Modes

| Mode | When | RPS | Queue | Context |
|------|------|-----|-------|---------|
| ECO | Battery, heat | 6 | 32 | 0.5× |
| BALANCED | Default | 16 | 64 | 1.0× |
| TURBO | Active work | 32 | 128 | 1.3× |
| AUTO | Let it choose | - | - | - |

## 🛡️ Safety Triggers

| Event | Trigger | Action |
|-------|---------|--------|
| **Thermal** | GPU > 82°C | Emergency throttle |
| **Overload** | CPU/GPU > 85% | Backpressure |
| **Errors** | Error rate > 1% | Throttle |
| **Brownout** | OOM, timeouts | Fallback model |
| **Battery** | < 30% charge | Force ECO |

## 📊 Targets

- CPU: 65%
- GPU: 70%
- RAM: 75%
- VRAM: 80%
- Temp: < 82°C

## 🔧 Config

Edit `config/llm.yaml`:

```yaml
autotune:
  mode: auto  # eco|balanced|turbo|auto
  targets:
    cpu: 0.65
    gpu: 0.70
    temp_max_c: 82
  loops:
    fast_period_s: 2
    slow_period_s: 90
```

## 📚 Full Docs

`📚_ADAPTIVE_GOVERNOR_COMPLETE_GUIDE.md`

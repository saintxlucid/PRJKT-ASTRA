# ASTRA OS — P1 Starter Kit (Transcendent v2.0)

A minimal, sovereign scaffold for Phase 1 of ASTRA OS. It captures the core
cognitive loop while staying dependency-light and easy to extend.

## Contents
- Cognitive Fusion Meta-Controller and Governor
- Emotional Context Engine with local-only signals
- Memory Semantic Compression service
- PQ Token Interface (Dilithium-ready with HMAC fallback)
- Forge Sandbox for constrained macro execution
- Configs, smoke tests, and demo workflow

## Quick Start
```powershell
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
pytest -q
python demo/demo_dayflow.py
```

## Next Steps
- Extend `MetaController.learn_macro` with your macro mining pipeline
- Implement real Lucid Protocol data loaders in `configs/lucid.yaml`
- Replace placeholder embeddings and PQ token signing with production modules
- Feed telemetry back into the governor to steer creativity at runtime

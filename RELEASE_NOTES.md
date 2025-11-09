# ASTRA Core v1.0 Release Notes

## Overview

This release marks the first stable version of ASTRA Core, featuring comprehensive safety guardrails, enhanced tool accuracy, and robust model deployment capabilities.

## Metrics & Gates

### Language Model Performance

- Base Perplexity: 6.42
- Current Perplexity: 6.42 (0% drift)
- Threshold: 7.062 (max +10% allowed)

### Tool Usage

- Base Accuracy: 92.5%
- Current Accuracy: 92.5%
- Minimum Required: 90%

### Model Stability

- Base Drift: 0%
- Current Drift: 0%
- Maximum Allowed: 7%

### Safety & Compliance

- Base Guardrail Score: 98.2%
- Current Score: 98.2%
- Minimum Required: 95%

## Key Features

### Evolution Engine

- Deterministic model builds
- Quantization profiles (Q5_K_M primary, Q4_K_M low-VRAM)
- RoPE scaling support
- Embedded provenance metadata

### Safety Systems

- Enhanced guardrail architecture
- Red-team evaluation suite
- Automatic drift detection
- Safety-first tool validation

### Developer Tools

- astramk build system
- gguf-validate gate checker
- gguf-commit deployment manager
- Comprehensive CLI suite

## Artifacts

### Primary Release

- GPT-OOS-20B.EVO.gguf (Q5_K_M)
- SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- Build: astramk v1.0.0
- Date: 2025-10-22

### Alternative Profiles

- GPT-OOS-20B.EVO.Q4.gguf (Low-VRAM)
- GPT-OOS-20B.EVO.LC.gguf (Long-Context)
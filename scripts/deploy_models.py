#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Model Download and Deployment Script for ASTRA Multi-Model Stack
==================================================================

Downloads all configured models and prepares them for deployment.

Usage:
    # Download all models
    python scripts/deploy_models.py --all
    
    # Download specific profile
    python scripts/deploy_models.py --profile gpu
    python scripts/deploy_models.py --profile edge
    
    # Download single model
    python scripts/deploy_models.py --model deepseek-v3.1
    
    # Verify existing models
    python scripts/deploy_models.py --verify
    
    # Convert HF model to GGUF
    python scripts/deploy_models.py --convert phi-4-mini --quantization Q5_K_M
"""
import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# Model registry with download info
MODELS = {
    # === PRIMARY REASONING (vLLM) ===
    "deepseek-v3.1": {
        "repo": "deepseek-ai/DeepSeek-V3.1",
        "size_gb": 80.0,
        "format": "safetensors",
        "backend": "vllm",
        "profile": "gpu",
        "priority": "high"
    },
    "mistral-large-2": {
        "repo": "mistralai/Mistral-Large-2-Instruct",
        "size_gb": 60.0,
        "format": "safetensors",
        "backend": "vllm",
        "profile": "gpu",
        "priority": "high"
    },
    
    # === VISION-LANGUAGE (vLLM) ===
    "llama-3.2-vision-11b": {
        "repo": "meta-llama/Llama-3.2-11B-Vision-Instruct",
        "size_gb": 24.0,
        "format": "safetensors",
        "backend": "vllm",
        "profile": "gpu",
        "priority": "medium"
    },
    "qwen-2.5-vl-7b": {
        "repo": "Qwen/Qwen2-VL-7B-Instruct",
        "size_gb": 16.0,
        "format": "safetensors",
        "backend": "vllm",
        "profile": "gpu",
        "priority": "medium"
    },
    
    # === FAST CHAT / EDGE (GGUF) ===
    "phi-4-mini": {
        "repo": "microsoft/phi-4-mini-instruct",
        "gguf_repo": "bartowski/phi-4-mini-instruct-GGUF",
        "gguf_file": "phi-4-mini-instruct-Q5_K_M.gguf",
        "size_gb": 4.0,
        "format": "gguf",
        "backend": "llamacpp",
        "profile": "edge",
        "priority": "high"
    },
    "qwen-2.5-1.5b": {
        "repo": "Qwen/Qwen2.5-1.5B-Instruct",
        "gguf_repo": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "gguf_file": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_gb": 1.2,
        "format": "gguf",
        "backend": "llamacpp",
        "profile": "edge",
        "priority": "medium"
    },
    "llama-3.2-3b": {
        "repo": "meta-llama/Llama-3.2-3B-Instruct",
        "gguf_repo": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "gguf_file": "Llama-3.2-3B-Instruct-Q5_K_M.gguf",
        "size_gb": 3.0,
        "format": "gguf",
        "backend": "llamacpp",
        "profile": "edge",
        "priority": "medium"
    },
    
    # === AUDIO ===
    "whisper-large-v3": {
        "repo": "openai/whisper-large-v3",
        "gguf_repo": "ggerganov/whisper.cpp",
        "gguf_file": "ggml-large-v3.bin",
        "size_gb": 3.1,
        "format": "gguf",
        "backend": "whisper",
        "profile": "audio",
        "priority": "high"
    },
    
    # === LEGACY ===
    "gpt-oss-20b": {
        "local_path": "models/gpt-oss-20b.q5_k_m.gguf",
        "size_gb": 13.0,
        "format": "gguf",
        "backend": "llamacpp",
        "profile": "cpu",
        "priority": "low"
    }
}


def check_disk_space(required_gb: float) -> bool:
    """Check if enough disk space available."""
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    stat = os.statvfs(models_dir)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    
    print(f"💾 Disk space: {free_gb:.1f}GB free, {required_gb:.1f}GB required")
    return free_gb >= required_gb * 1.2  # 20% buffer


def download_hf_model(repo: str, output_dir: Path, file: str = None) -> bool:
    """Download model from HuggingFace using huggingface-cli."""
    try:
        cmd = ["huggingface-cli", "download", repo]
        if file:
            cmd.extend(["--include", file])
        cmd.extend(["--local-dir", str(output_dir), "--local-dir-use-symlinks", "False"])
        
        print(f"📥 Downloading {repo}...")
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed: {e}")
        return False


def verify_model(path: Path, expected_size_gb: float) -> bool:
    """Verify model integrity by checking size."""
    if not path.exists():
        return False
    
    # Check size
    if path.is_dir():
        actual_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    else:
        actual_size = path.stat().st_size
    
    actual_gb = actual_size / (1024**3)
    expected_min = expected_size_gb * 0.9  # Allow 10% variance
    expected_max = expected_size_gb * 1.1
    
    if expected_min <= actual_gb <= expected_max:
        print(f"✅ {path.name}: {actual_gb:.1f}GB (valid)")
        return True
    else:
        print(f"⚠️ {path.name}: {actual_gb:.1f}GB (expected ~{expected_size_gb:.1f}GB)")
        return False


def download_model(model_name: str, spec: Dict) -> bool:
    """Download a single model."""
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # Check local path first
    if "local_path" in spec:
        path = Path(spec["local_path"])
        if path.exists():
            print(f"✅ {model_name}: Already exists locally")
            return verify_model(path, spec["size_gb"])
        else:
            print(f"⚠️ {model_name}: Local path not found: {path}")
            return False
    
    # Download from HuggingFace
    if spec["format"] == "gguf" and "gguf_repo" in spec:
        # Download GGUF file
        output_file = models_dir / spec["gguf_file"]
        if output_file.exists():
            print(f"✅ {model_name}: Already downloaded")
            return verify_model(output_file, spec["size_gb"])
        
        return download_hf_model(
            spec["gguf_repo"],
            models_dir,
            spec["gguf_file"]
        )
    
    elif spec["format"] == "safetensors" and "repo" in spec:
        # Download full model directory
        output_dir = models_dir / model_name
        if output_dir.exists():
            print(f"✅ {model_name}: Already downloaded")
            return verify_model(output_dir, spec["size_gb"])
        
        return download_hf_model(spec["repo"], output_dir)
    
    print(f"❌ {model_name}: Unknown format or missing repo")
    return False


def download_profile(profile: str) -> bool:
    """Download all models for a specific profile."""
    profile_models = {
        name: spec for name, spec in MODELS.items()
        if spec.get("profile") == profile
    }
    
    if not profile_models:
        print(f"❌ No models found for profile: {profile}")
        return False
    
    # Calculate total size
    total_gb = sum(spec["size_gb"] for spec in profile_models.values())
    if not check_disk_space(total_gb):
        print(f"❌ Insufficient disk space for profile: {profile}")
        return False
    
    # Download models
    print(f"\n📦 Downloading {len(profile_models)} models for profile: {profile}")
    print(f"   Total size: {total_gb:.1f}GB\n")
    
    success_count = 0
    for name, spec in profile_models.items():
        if download_model(name, spec):
            success_count += 1
    
    print(f"\n✅ Downloaded {success_count}/{len(profile_models)} models")
    return success_count == len(profile_models)


def verify_all() -> bool:
    """Verify all models in registry."""
    print("🔍 Verifying models...")
    
    valid_count = 0
    for name, spec in MODELS.items():
        if "local_path" in spec:
            path = Path(spec["local_path"])
        elif spec["format"] == "gguf":
            path = Path("models") / spec.get("gguf_file", f"{name}.gguf")
        else:
            path = Path("models") / name
        
        if verify_model(path, spec["size_gb"]):
            valid_count += 1
    
    print(f"\n✅ {valid_count}/{len(MODELS)} models valid")
    return valid_count == len(MODELS)


def main():
    parser = argparse.ArgumentParser(description="ASTRA Model Deployment")
    parser.add_argument("--all", action="store_true", help="Download all models")
    parser.add_argument("--profile", choices=["gpu", "cpu", "edge", "audio"], help="Download profile")
    parser.add_argument("--model", help="Download specific model")
    parser.add_argument("--verify", action="store_true", help="Verify existing models")
    parser.add_argument("--list", action="store_true", help="List available models")
    
    args = parser.parse_args()
    
    if args.list:
        print("\n📋 Available models:\n")
        for name, spec in MODELS.items():
            print(f"  {name:25s} {spec['size_gb']:6.1f}GB  {spec['profile']:8s}  {spec['backend']:10s}")
        return 0
    
    if args.verify:
        return 0 if verify_all() else 1
    
    if args.all:
        print("📦 Downloading all models...")
        for name, spec in MODELS.items():
            download_model(name, spec)
        return 0
    
    if args.profile:
        return 0 if download_profile(args.profile) else 1
    
    if args.model:
        if args.model not in MODELS:
            print(f"❌ Unknown model: {args.model}")
            return 1
        return 0 if download_model(args.model, MODELS[args.model]) else 1
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Hardware detection for ASTRA Core

Detects hardware capabilities and exposes optimal runtime variables.
"""

import torch
import psutil
import platform
import json


def detect():
    """Detect hardware capabilities"""
    gpu = torch.cuda.is_available()
    return {
        "gpu": gpu,
        "gpu_name": torch.cuda.get_device_name(0) if gpu else "CPU",
        "ram_gb": round(psutil.virtual_memory().total/1e9, 1),
        "os": platform.system(),
        "vram_gb": round(torch.cuda.get_device_properties(0).total_memory/1e9, 1) if gpu else 0
    }


if __name__ == "__main__":
    print(json.dumps(detect()))
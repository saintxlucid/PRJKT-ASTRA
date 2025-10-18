"""
Ableton / FL Studio automation plugin for ASTRA Task Agent.

Design: Permissioned actions with no arbitrary shell execution.
Extends with real API (AbletonOSC, custom scripts) under explicit user approval.

Part of ASTRA Ascension Stack V2 Add-ons
"""
import os
import subprocess
import sys
import platform
from pathlib import Path
from typing import Dict, Any

import structlog

logger = structlog.get_logger()

# Signal directory for DAW communication
SIGNAL_DIR = Path(".astra_signals")
SIGNAL_DIR.mkdir(exist_ok=True)


def _open_file(path: str) -> None:
    """
    Open file with OS default application.
    
    Args:
        path: Absolute path to file
    """
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])


def open_project(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Open DAW project file.
    
    Args:
        args: { "path": "C:/Projects/ALTER.als" }
        
    Returns:
        { "opened": str, "status": str }
        
    Raises:
        ValueError: If project file not found
    """
    path = args.get("path")
    
    if not path:
        raise ValueError("Missing required argument: path")
    
    path_obj = Path(path)
    
    if not path_obj.exists():
        raise ValueError(f"Project file not found: {path}")
    
    # Validate file extension (Ableton .als, FL Studio .flp)
    valid_extensions = {".als", ".flp", ".rpp"}  # Ableton, FL, Reaper
    if path_obj.suffix.lower() not in valid_extensions:
        logger.warning("daw_unknown_extension", path=path, suffix=path_obj.suffix)
    
    logger.info("daw_open_project", path=path)
    
    try:
        _open_file(str(path_obj.absolute()))
        return {
            "opened": str(path_obj.absolute()),
            "status": "success",
            "message": f"Opened {path_obj.name}"
        }
    except Exception as e:
        logger.error("daw_open_failed", path=path, error=str(e))
        raise ValueError(f"Failed to open project: {e}")


def set_bpm(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set desired BPM for DAW.
    
    Writes BPM to signal file for DAW-side watcher script to pick up.
    Real BPM control requires Live API, OSC, or custom scripting.
    
    Args:
        args: { "bpm": 160 }
        
    Returns:
        { "desired_bpm": float, "signal_file": str, "note": str }
    """
    bpm = args.get("bpm", 140)
    
    try:
        bpm_float = float(bpm)
        if not (20 <= bpm_float <= 999):
            raise ValueError("BPM must be between 20 and 999")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid BPM value: {bpm}") from e
    
    # Write to signal file
    signal_file = SIGNAL_DIR / "desired_bpm.txt"
    
    with open(signal_file, "w", encoding="utf-8") as f:
        f.write(f"{bpm_float}\n")
    
    logger.info("daw_bpm_signal", bpm=bpm_float, signal_file=str(signal_file))
    
    return {
        "desired_bpm": bpm_float,
        "signal_file": str(signal_file.absolute()),
        "status": "success",
        "note": f"BPM signal written. Have your DAW watcher read: {signal_file.absolute()}"
    }


def set_track_arm(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Signal to arm/disarm track for recording.
    
    Args:
        args: { "track_number": 1, "armed": true }
        
    Returns:
        { "track_number": int, "armed": bool, "signal_file": str }
    """
    track_number = args.get("track_number")
    armed = args.get("armed", True)
    
    if track_number is None:
        raise ValueError("Missing required argument: track_number")
    
    try:
        track_int = int(track_number)
        if track_int < 1:
            raise ValueError("Track number must be >= 1")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid track_number: {track_number}") from e
    
    signal_file = SIGNAL_DIR / f"track_{track_int}_arm.txt"
    
    with open(signal_file, "w", encoding="utf-8") as f:
        f.write(f"{'armed' if armed else 'disarmed'}\n")
    
    logger.info("daw_track_arm_signal", track=track_int, armed=armed, signal_file=str(signal_file))
    
    return {
        "track_number": track_int,
        "armed": bool(armed),
        "signal_file": str(signal_file.absolute()),
        "status": "success",
        "note": f"Track arm signal written: {signal_file.absolute()}"
    }


def trigger_scene(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Signal to trigger Ableton Live scene.
    
    Args:
        args: { "scene_number": 1 }
        
    Returns:
        { "scene_number": int, "signal_file": str }
    """
    scene_number = args.get("scene_number")
    
    if scene_number is None:
        raise ValueError("Missing required argument: scene_number")
    
    try:
        scene_int = int(scene_number)
        if scene_int < 1:
            raise ValueError("Scene number must be >= 1")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid scene_number: {scene_number}") from e
    
    signal_file = SIGNAL_DIR / "trigger_scene.txt"
    
    with open(signal_file, "w", encoding="utf-8") as f:
        f.write(f"{scene_int}\n")
    
    logger.info("daw_scene_trigger", scene=scene_int, signal_file=str(signal_file))
    
    return {
        "scene_number": scene_int,
        "signal_file": str(signal_file.absolute()),
        "status": "success",
        "note": f"Scene trigger signal written: {signal_file.absolute()}"
    }


def get_signals(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current signal directory state.
    
    Args:
        args: {} (no arguments required)
        
    Returns:
        { "signal_dir": str, "signals": List[str] }
    """
    signals = [f.name for f in SIGNAL_DIR.glob("*.txt")]
    
    return {
        "signal_dir": str(SIGNAL_DIR.absolute()),
        "signals": sorted(signals),
        "count": len(signals),
        "status": "success"
    }


def clear_signals(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clear all signal files.
    
    Args:
        args: {} (no arguments required)
        
    Returns:
        { "cleared": int, "status": str }
    """
    cleared = 0
    
    for signal_file in SIGNAL_DIR.glob("*.txt"):
        try:
            signal_file.unlink()
            cleared += 1
        except Exception as e:
            logger.warning("signal_clear_failed", file=signal_file.name, error=str(e))
    
    logger.info("daw_signals_cleared", count=cleared)
    
    return {
        "cleared": cleared,
        "status": "success",
        "message": f"Cleared {cleared} signal file(s)"
    }

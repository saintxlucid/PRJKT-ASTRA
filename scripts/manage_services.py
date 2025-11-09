#!/usr/bin/env python3
"""Utility to manage the local ASTRA stack (llama.cpp + API server).

This script provides a tiny CLI with ``start``, ``stop`` and ``status`` commands
so you can quickly bring the full stack up or tear it down without manually
launching each component.  It assumes the repository layout from the Project
ASTRA workspace and can be customised through environment variables when
needed.
"""

from __future__ import annotations

import argparse
import os
# Standard library modules
import signal
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Set

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = REPO_ROOT / "runtime"
DEFAULT_LOG_DIR = REPO_ROOT / "logs"
LLM_PROFILE_CONFIG = REPO_ROOT / "config" / "llm_launcher.yaml"

# Allow overrides through environment variables so users can point at custom builds.
LLAMA_BIN = Path(
    os.environ.get(
        "ASTRA_LLAMACPP_BIN",
        (REPO_ROOT
         / "astra-local" / "backend" / "bin" / "llama.cpp" / "build" / "bin" / "Release"
         / ("llama-server.exe" if os.name == "nt" else "llama-server")),
    )
)
LLAMA_MODEL = Path(
    os.environ.get(
        "ASTRA_LLAMACPP_MODEL",
        REPO_ROOT / "astra-local" / "data" / "models" / "gpt-oss-20b.Q4_K_M.gguf",
    )
)
LLAMA_HOST = os.environ.get("ASTRA_LLAMACPP_HOST", "127.0.0.1")
LLAMA_PORT = int(os.environ.get("ASTRA_LLAMACPP_PORT", "8001"))
LLAMA_EXTRA_ARGS = os.environ.get("ASTRA_LLAMACPP_ARGS", "--ctx-size 4096 --n-gpu-layers 0")

ASTRA_HOST = os.environ.get("ASTRA_API_HOST", "0.0.0.0")
ASTRA_PORT = int(os.environ.get("ASTRA_API_PORT", "8080"))
ASTRA_CHECK_HOST = "127.0.0.1" if ASTRA_HOST in {"0.0.0.0", "::"} else ASTRA_HOST

LLAMA_PID_FILE = DEFAULT_RUNTIME_DIR / "llama_server.pid"
ASTRA_PID_FILE = DEFAULT_RUNTIME_DIR / "astra_api.pid"

CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_extra_args(raw_args: str) -> list[str]:
    return raw_args.split()


def load_llm_profile(profile: str) -> Dict[str, Any]:
    """Load llama.cpp launch settings from configuration profiles.

    Profiles live in ``config/llm_launcher.yaml`` and can override the binary,
    model path, host/port, additional CLI arguments, and environment variables
    used when spawning the llama.cpp server.
    """

    base: Dict[str, Any] = {
        "binary": LLAMA_BIN,
        "model": LLAMA_MODEL,
        "host": LLAMA_HOST,
        "port": LLAMA_PORT,
        "extra_args": parse_extra_args(LLAMA_EXTRA_ARGS),
        "env": {},
    }

    if not LLM_PROFILE_CONFIG.exists():
        if profile != "default":
            raise ValueError(f"Unknown LLM profile '{profile}' (no profile file present)")
        return base

    raw_config = yaml.safe_load(LLM_PROFILE_CONFIG.read_text()) or {}
    profiles = raw_config.get("profiles", {})
    if profile == "default" and profile not in profiles:
        return base

    def resolve(name: str, trail: Set[str]) -> Dict[str, Any]:
        if name in trail:
            raise ValueError(f"Profile inheritance loop detected for '{name}'")
        profile_payload = profiles.get(name)
        if profile_payload is None:
            raise KeyError(name)

        merged: Dict[str, Any] = {}
        extends = profile_payload.get("extends")
        if extends:
            merged.update(resolve(str(extends), trail | {name}))

        for key, value in profile_payload.items():
            if key == "extends":
                continue
            merged[key] = value

        return merged

    try:
        overrides = resolve(profile, set())
    except KeyError:
        raise ValueError(f"Unknown LLM profile '{profile}'") from None

    settings = dict(base)
    if "binary" in overrides:
        settings["binary"] = resolve_path(str(overrides["binary"]))
    if "model" in overrides:
        settings["model"] = resolve_path(str(overrides["model"]))
    if "host" in overrides:
        settings["host"] = str(overrides["host"])
    if "port" in overrides:
        settings["port"] = int(overrides["port"])
    if "extra_args" in overrides:
        extra_args = overrides["extra_args"]
        if isinstance(extra_args, str):
            settings["extra_args"] = parse_extra_args(extra_args)
        elif isinstance(extra_args, list):
            settings["extra_args"] = [str(item) for item in extra_args]
        else:
            raise ValueError("extra_args must be a string or a list")
    if "env" in overrides:
        env_overrides = overrides["env"]
        if not isinstance(env_overrides, dict):
            raise ValueError("env must be a mapping of environment variables")
        settings["env"] = {str(k): str(v) for k, v in env_overrides.items()}

    return settings


def get_selected_components(selection: str) -> Set[str]:
    if selection == "all":
        return {"llm", "api"}
    return {selection}


def resolve_path(value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (REPO_ROOT / candidate).resolve()
    return candidate


def resolve_directory_arg(arg_value: Optional[str], env_var: str, default: Path) -> Path:
    candidate = arg_value or os.environ.get(env_var)
    if candidate:
        return resolve_path(candidate)
    return default


def is_port_listening(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        try:
            sock.connect((host, port))
        except (ConnectionRefusedError, OSError, socket.timeout):
            return False
    return True


def read_pid(pid_file: Path) -> Optional[int]:
    try:
        return int(pid_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def write_pid(pid_file: Path, pid: int) -> None:
    pid_file.write_text(str(pid))


def remove_pid(pid_file: Path) -> None:
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass


def process_running(pid: Optional[int]) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def terminate_pid(pid: int, *, name: str) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return

    timeout = time.time() + 10
    while process_running(pid) and time.time() < timeout:
        time.sleep(0.1)

    if process_running(pid):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            sigkill = getattr(signal, "SIGKILL", signal.SIGTERM)
            try:
                os.kill(pid, sigkill)
            except ProcessLookupError:
                return


def start_llama(*, logs_dir: Path, runtime_dir: Path, profile: str) -> tuple[bool, str, int]:
    settings = load_llm_profile(profile)
    host = str(settings["host"])
    port = int(settings["port"])

    if is_port_listening(host, port):
        return False, host, port

    binary: Path = settings["binary"]
    model: Path = settings["model"]
    extra_args: list[str] = settings.get("extra_args", [])
    env_overrides: Dict[str, str] = settings.get("env", {})

    ensure_directory(logs_dir)
    ensure_directory(runtime_dir)

    if not binary.exists():
        raise FileNotFoundError(f"llama-server binary not found at {binary}")
    if not model.exists():
        raise FileNotFoundError(f"Model file not found at {model}")

    llama_log = (logs_dir / "llama-server.log").open("a", buffering=1)

    args = [str(binary), "-m", str(model), "--host", host, "--port", str(port)]
    args.extend(extra_args)

    env = os.environ.copy()
    env.update(env_overrides)

    creationflags = CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    preexec_fn = os.setsid if os.name != "nt" and hasattr(os, "setsid") else None

    proc = subprocess.Popen(
        args,
        stdout=llama_log,
        stderr=subprocess.STDOUT,
        cwd=binary.parent,
        creationflags=creationflags,
        preexec_fn=preexec_fn,
        env=env,
    )
    write_pid(runtime_dir / LLAMA_PID_FILE.name, proc.pid)
    return True, host, port


def start_astra(*, logs_dir: Path, runtime_dir: Path) -> bool:
    if is_port_listening(ASTRA_CHECK_HOST, ASTRA_PORT):
        return False

    ensure_directory(logs_dir)
    ensure_directory(runtime_dir)

    astra_log = (logs_dir / "astra-api.log").open("a", buffering=1)

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str(REPO_ROOT / "src")
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = src_path

    creationflags = CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    preexec_fn = os.setsid if os.name != "nt" and hasattr(os, "setsid") else None

    proc = subprocess.Popen(
        [sys.executable, "run_server.py"],
        cwd=REPO_ROOT,
        stdout=astra_log,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=creationflags,
        preexec_fn=preexec_fn,
    )
    write_pid(runtime_dir / ASTRA_PID_FILE.name, proc.pid)
    return True


def start_services(args: argparse.Namespace) -> None:
    runtime_dir = resolve_directory_arg(args.runtime_dir, "ASTRA_RUNTIME_DIR", DEFAULT_RUNTIME_DIR)
    logs_dir = resolve_directory_arg(args.logs_dir, "ASTRA_LOG_DIR", DEFAULT_LOG_DIR)
    components = get_selected_components(args.components)

    messages: list[str] = []
    started_any = False

    if "llm" in components:
        llama_started, llama_host, llama_port = start_llama(
            logs_dir=logs_dir,
            runtime_dir=runtime_dir,
            profile=args.profile,
        )
        if llama_started:
            started_any = True
            messages.append(
                f"Started llama.cpp server (profile '{args.profile}') on {llama_host}:{llama_port}"
            )
        else:
            messages.append(
                f"llama.cpp server already running on {llama_host}:{llama_port}; skipped."
            )

    if "api" in components:
        astra_started = start_astra(logs_dir=logs_dir, runtime_dir=runtime_dir)
        if astra_started:
            started_any = True
            messages.append(
                f"Started ASTRA API on http://{ASTRA_CHECK_HOST}:{ASTRA_PORT} (binding {ASTRA_HOST})"
            )
        else:
            messages.append("ASTRA API already running; skipped.")

    if not messages:
        messages.append("No components selected; nothing to start.")
    elif not started_any:
        messages.insert(0, "Selected components already appear to be running.")

    for message in messages:
        print(message)


def stop_services(args: argparse.Namespace) -> None:
    runtime_dir = resolve_directory_arg(args.runtime_dir, "ASTRA_RUNTIME_DIR", DEFAULT_RUNTIME_DIR)
    components = get_selected_components(args.components)

    messages: list[str] = []
    stopped_any = False

    if "llm" in components:
        llama_pid_path = runtime_dir / LLAMA_PID_FILE.name
        llama_pid = read_pid(llama_pid_path)
        if llama_pid and process_running(llama_pid):
            terminate_pid(llama_pid, name="llama.cpp server")
            stopped_any = True
            messages.append("Stopped llama.cpp server.")
        elif llama_pid:
            messages.append("llama.cpp server PID file existed but process was not running (cleaned up).")
        else:
            messages.append("llama.cpp server was not running.")
        remove_pid(llama_pid_path)

    if "api" in components:
        astra_pid_path = runtime_dir / ASTRA_PID_FILE.name
        astra_pid = read_pid(astra_pid_path)
        if astra_pid and process_running(astra_pid):
            terminate_pid(astra_pid, name="ASTRA API")
            stopped_any = True
            messages.append("Stopped ASTRA API.")
        elif astra_pid:
            messages.append("ASTRA API PID file existed but process was not running (cleaned up).")
        else:
            messages.append("ASTRA API was not running.")
        remove_pid(astra_pid_path)

    if not messages:
        messages.append("No components selected; nothing to stop.")
    elif not stopped_any:
        messages.insert(0, "No managed processes were running for the selected components.")

    for message in messages:
        print(message)


def restart_services(args: argparse.Namespace) -> None:
    stop_services(args)
    # Give the OS a brief moment to release ports before restarting.
    time.sleep(0.5)
    start_services(args)


def status_services(args: argparse.Namespace) -> None:
    runtime_dir = resolve_directory_arg(args.runtime_dir, "ASTRA_RUNTIME_DIR", DEFAULT_RUNTIME_DIR)
    components = get_selected_components(args.components)

    if "llm" in components:
        llama_settings = load_llm_profile(args.profile)
        llama_host = str(llama_settings["host"])
        llama_port = int(llama_settings["port"])
        llama_pid_path = runtime_dir / LLAMA_PID_FILE.name
        llama_pid = read_pid(llama_pid_path)
        llama_running = process_running(llama_pid) or is_port_listening(llama_host, llama_port)

        print(
            f"llama.cpp server ({args.profile} profile):",
            "running" if llama_running else "stopped",
        )
        print(f"  listen address: {llama_host}:{llama_port}")
        if llama_pid:
            print(f"  pid file: {llama_pid}")

    if "api" in components:
        astra_pid_path = runtime_dir / ASTRA_PID_FILE.name
        astra_pid = read_pid(astra_pid_path)
        astra_running = process_running(astra_pid) or is_port_listening(ASTRA_CHECK_HOST, ASTRA_PORT)

        print("ASTRA API:", "running" if astra_running else "stopped")
        print(f"  listen address: http://{ASTRA_CHECK_HOST}:{ASTRA_PORT} (binding {ASTRA_HOST})")
        if astra_pid:
            print(f"  pid file: {astra_pid}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="manage_services.py",
        description="Manage the local ASTRA stack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
                        Examples:
                            python scripts/manage_services.py start
                            python scripts/manage_services.py start --components llm --profile quantized
                            python scripts/manage_services.py restart
                            python scripts/manage_services.py status --components api
                            python scripts/manage_services.py stop

            Environment variables:
              ASTRA_LLAMACPP_BIN   Override llama.cpp binary location
              ASTRA_LLAMACPP_MODEL Path to GGUF model
              ASTRA_LLAMACPP_ARGS  Extra arguments passed to llama-server
                            ASTRA_API_PORT       Override API port (default 8080)
                            ASTRA_RUNTIME_DIR    Custom runtime directory for PID files
                            ASTRA_LOG_DIR        Custom log directory
            """
        ),
    )

    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "restart"],
        help="Action to perform",
    )
    parser.add_argument("--logs-dir", dest="logs_dir", help="Directory to place log files")
    parser.add_argument("--runtime-dir", dest="runtime_dir", help="Directory for PID files")
    parser.add_argument(
        "--components",
        choices=["all", "llm", "api"],
        default="all",
        help="Which component(s) to manage (default: all)",
    )
    parser.add_argument(
        "--profile",
        dest="profile",
        default="default",
        help="LLM profile defined in config/llm_launcher.yaml (default: default)",
    )

    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(list(argv) if argv is not None else None)

    if args.command == "start":
        start_services(args)
    elif args.command == "stop":
        stop_services(args)
    elif args.command == "restart":
        restart_services(args)
    else:
        status_services(args)


if __name__ == "__main__":
    main()

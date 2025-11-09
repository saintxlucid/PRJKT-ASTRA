# Service Management Cheat Sheet

Keep both parts of ASTRA (the llama.cpp inference backend and the FastAPI API server) in sync with the helper script.

## Prerequisites

- The virtual environment is created at `.venv/`
- Model file available at `astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf`
- Llama.cpp server binary located under `astra-local/backend/bin/llama.cpp/build/bin/Release/`

## Quick commands

```powershell
# Start llama.cpp and the ASTRA API together
X:/PROJECT_ASTRA/.venv/Scripts/python.exe scripts\manage_services.py start

# Start only the llama.cpp server with a non-default profile from config/llm_launcher.yaml
X:/PROJECT_ASTRA/.venv/Scripts/python.exe scripts\manage_services.py start --components llm --profile quantized

# Bounce everything in one go
X:/PROJECT_ASTRA/.venv/Scripts/python.exe scripts\manage_services.py restart

# Inspect just the API status
X:/PROJECT_ASTRA/.venv/Scripts/python.exe scripts\manage_services.py status --components api

# Stop everything started by the script
X:/PROJECT_ASTRA/.venv/Scripts/python.exe scripts\manage_services.py stop
```

> **Tip:** Override defaults with environment variables such as `ASTRA_LLAMACPP_BIN`, `ASTRA_LLAMACPP_MODEL`, `ASTRA_API_PORT`, `ASTRA_RUNTIME_DIR`, and `ASTRA_LOG_DIR` when needed. If `python` on your `PATH` does not point to the project virtual environment, call the script with the explicit `.venv` interpreter as shown above.

### Useful flags

- `--components {all|llm|api}` — choose which part of the stack to act on (default `all`)
- `--profile <name>` — pick an LLM launch profile defined in `config/llm_launcher.yaml` (default `default`)
- `--runtime-dir <path>` — place PID files somewhere else (or set `ASTRA_RUNTIME_DIR`)
- `--logs-dir <path>` — redirect log files (or set `ASTRA_LOG_DIR`)

## What the script does

- Launches llama.cpp with the selected profile (defaults to `config/llm_launcher.yaml` → `default`) on its configured host/port
- Starts the ASTRA API (`run_server.py`) on port `8080` using the current Python interpreter
- Creates `runtime/` for PID tracking and `logs/` for stdout/stderr capture (respects CLI flags and `ASTRA_RUNTIME_DIR`/`ASTRA_LOG_DIR`)
- Skips components already active on their respective ports
- Supports `restart` to stop and relaunch the selected components

## LLM profiles

Profiles live in `config/llm_launcher.yaml` and let you customize binaries, models, ports, arguments, and environment variables.

```yaml
profiles:
	default:
		binary: astra-local/backend/bin/llama.cpp/build/bin/Release/llama-server.exe
		model: astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf
		extra_args:
			- --ctx-size
			- "4096"
			- --n-gpu-layers
			- "0"

	quantized:
		extends: default
		extra_args:
			- --ctx-size
			- "4096"
			- --n-gpu-layers
			- "35"
```

Create new entries and point `--profile` at them to spin up variants quickly. Add an `env` section (key/value pairs) to inject extra environment variables when running llama.cpp.

## Troubleshooting

- **Binary not found**: Set `ASTRA_LLAMACPP_BIN` to the compiled llama server path.
- **Model missing**: Set `ASTRA_LLAMACPP_MODEL` if your GGUF lives elsewhere.
- **Ports in use**: Make sure nothing else is bound to ports `8001` or `8080` before running `start`.
- **Unexpected stop**: Check `logs/llama-server.log` and `logs/astra-api.log`.

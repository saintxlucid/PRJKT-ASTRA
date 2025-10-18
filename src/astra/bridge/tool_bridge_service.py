# src/astra/bridge/tool_bridge_service.py
"""
ASTRA Tool Bridge - Production-Ready Service
FastAPI service with API-key auth, adapter registration, quotas, and audit logging.
"""
import os
import time
import json
import shlex
import logging
import subprocess
from typing import Dict, Any, Callable, Optional, Tuple
from fastapi import FastAPI, Header, HTTPException, Request, Depends
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import PlainTextResponse, JSONResponse

# --- CONFIG ---
API_KEY = os.environ.get("BRIDGE_API_KEY", "changeme")  # legacy single key
API_KEYS_FILE = os.environ.get("BRIDGE_KEYS_FILE")  # JSON file with multiple keys + scopes
AUDIT_LOG = os.environ.get("BRIDGE_AUDIT_LOG", "data/bridge_audit.log")
MAX_CONCURRENT = int(os.environ.get("BRIDGE_MAX_CONCURRENT", "8"))
DEFAULT_TIMEOUT = int(os.environ.get("BRIDGE_DEFAULT_TIMEOUT", "30"))
ENFORCE_PER_TOOL_SCOPE = os.environ.get("BRIDGE_ENFORCE_PER_TOOL_SCOPE", "false").lower() in ("1","true","yes")

# Rate limiting / quotas
USAGE_DB_PATH = os.environ.get("BRIDGE_USAGE_DB", "data/bridge_usage.json")
DEFAULT_RPM = int(os.environ.get("BRIDGE_DEFAULT_RPM", "60"))
DEFAULT_DAILY = int(os.environ.get("BRIDGE_DEFAULT_DAILY", "5000"))

# --- LOGGING / AUDIT ---
logger = logging.getLogger("bridge")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# Append-only audit file
os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)

def audit_event(event: Dict[str, Any]):
    """Write append-only audit log entry"""
    event["ts"] = time.time()
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

# --- PROMETHEUS METRICS ---
CALLS = Counter("bridge_calls_total", "Total tool calls", ["tool", "status"])
DURATION = Histogram("bridge_call_duration_seconds", "Duration of tool calls", ["tool"])

# --- FASTAPI APP ---
app = FastAPI(
    title="ASTRA Tool Bridge",
    version="1.0.0",
    description="Production-ready tool execution service with auth, quotas, and audit logging"
)

# --- AUTH DEPENDENCY ---
def _load_keys_file() -> Dict[str, Dict[str, Any]]:
    """Load keys from file if BRIDGE_KEYS_FILE is set; format: {"<token>": {"scopes":[...], "rpm":int, "daily":int}}"""
    keys: Dict[str, Dict[str, Any]] = {}
    if not API_KEYS_FILE:
        return keys
    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                keys = data
    except Exception as e:
        logger.error(f"Failed to load keys file: {e}")
    return keys

_KEYS_CACHE: Dict[str, Dict[str, Any]] = _load_keys_file()
_KEYS_MTIME: float = os.path.getmtime(API_KEYS_FILE) if API_KEYS_FILE and os.path.exists(API_KEYS_FILE) else 0.0

def _maybe_reload_keys():
    global _KEYS_CACHE, _KEYS_MTIME
    if not API_KEYS_FILE:
        return
    try:
        mtime = os.path.getmtime(API_KEYS_FILE)
        if mtime != _KEYS_MTIME:
            _KEYS_CACHE = _load_keys_file()
            _KEYS_MTIME = mtime
            logger.info("reloaded_keys_file", path=API_KEYS_FILE, count=len(_KEYS_CACHE))
    except Exception:
        pass

# Usage tracking (rate limiting + quotas)
_RPM_WINDOW: Dict[str, Tuple[int,int]] = {}  # token -> (window_start_epoch_minute, count)
_DAILY_USAGE: Dict[str, Dict[str, int]] = {}  # token -> {"yyyymmdd": count}

def _load_usage_db():
    global _DAILY_USAGE
    try:
        if os.path.exists(USAGE_DB_PATH):
            with open(USAGE_DB_PATH, "r", encoding="utf-8") as f:
                _DAILY_USAGE = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load usage DB: {e}")

def _save_usage_db():
    try:
        os.makedirs(os.path.dirname(USAGE_DB_PATH), exist_ok=True)
        with open(USAGE_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(_DAILY_USAGE, f)
    except Exception as e:
        logger.error(f"Failed to save usage DB: {e}")

_load_usage_db()

def _check_and_increment_limits(token: str, rpm_limit: int, daily_limit: int):
    # RPM: fixed window per minute
    now = int(time.time())
    current_min = now // 60
    win = _RPM_WINDOW.get(token)
    if not win or win[0] != current_min:
        _RPM_WINDOW[token] = (current_min, 1)
    else:
        if win[1] >= rpm_limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded (rpm)")
        _RPM_WINDOW[token] = (win[0], win[1] + 1)

    # Daily quota (UTC date)
    from datetime import datetime, timezone
    date_key = datetime.now(timezone.utc).strftime("%Y%m%d")
    t_usage = _DAILY_USAGE.get(token, {})
    used = int(t_usage.get(date_key, 0))
    if used >= daily_limit:
        raise HTTPException(status_code=429, detail="Daily quota exceeded")
    t_usage[date_key] = used + 1
    _DAILY_USAGE[token] = t_usage
    _save_usage_db()

def _get_token_record(token: str) -> Dict[str, Any]:
    # Prefer keys file if present
    _maybe_reload_keys()
    if _KEYS_CACHE:
        rec = _KEYS_CACHE.get(token)
        if rec:
            return {
                "scopes": rec.get("scopes", []),
                "rpm": int(rec.get("rpm", DEFAULT_RPM)),
                "daily": int(rec.get("daily", DEFAULT_DAILY))
            }
        # not found in keys file
        raise HTTPException(status_code=403, detail="Invalid API Key")
    # fallback single-key mode
    if token == API_KEY:
        return {"scopes": ["admin", "tool:call"], "rpm": DEFAULT_RPM, "daily": DEFAULT_DAILY}
    raise HTTPException(status_code=403, detail="Invalid API Key")

def require_scope(required_scope: str):
    def dep(x_api_key: str = Header(...)):
        rec = _get_token_record(x_api_key)
        scopes = rec.get("scopes", [])
        if required_scope not in scopes and "admin" not in scopes:
            raise HTTPException(status_code=403, detail="Insufficient scope")
        # rate limit checks
        _check_and_increment_limits(x_api_key, rec.get("rpm", DEFAULT_RPM), rec.get("daily", DEFAULT_DAILY))
        return x_api_key
    return dep

def require_api_key(x_api_key: str = Header(...)):
    # Backward-compat: any valid token returns
    _ = _get_token_record(x_api_key)
    return x_api_key

# --- MODELS ---
class ToolCall(BaseModel):
    """Tool execution request"""
    tool_name: str
    args: Dict[str, Any] = {}
    request_id: Optional[str] = None

class ToolResult(BaseModel):
    """Tool execution response"""
    ok: bool
    result: Optional[Any] = None
    error: Optional[str] = None

# --- TOOL REGISTRY ---
TOOLS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
TOOL_ALLOWLIST: Dict[str, Dict[str, Any]] = {}  # e.g. {"shell": {"cmds": ["ls","du"]}, ...}
TOOL_TIMEOUTS: Dict[str, int] = {}

def register_tool(
    name: str,
    fn: Callable[[Dict[str, Any]], Any],
    allowlist: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None
):
    """
    Register a tool adapter with optional allowlist and timeout.
    
    Args:
        name: Tool identifier
        fn: Tool execution function
        allowlist: Allowed operations/paths dict
        timeout: Per-tool timeout override (seconds)
    """
    TOOLS[name] = fn
    if allowlist:
        TOOL_ALLOWLIST[name] = allowlist
    if timeout:
        TOOL_TIMEOUTS[name] = timeout
    logger.info(f"Tool registered: {name} (timeout={timeout or DEFAULT_TIMEOUT}s)")

# --- TOOL ADAPTERS ---

def shell_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute whitelisted shell commands only.
    
    Args:
        args: {"cmd": "ls -la"}
    
    Returns:
        {"stdout": str, "stderr": str, "returncode": int}
    """
    cmd = args.get("cmd", "")
    if not cmd:
        raise ValueError("missing 'cmd' argument")
    
    parts = shlex.split(cmd)
    base = parts[0]
    allowed = TOOL_ALLOWLIST.get("shell", {}).get("cmds", [])
    
    if base not in allowed:
        raise ValueError(f"Command not allowed: {base}. Allowed: {allowed}")
    
    timeout = TOOL_TIMEOUTS.get("shell", DEFAULT_TIMEOUT)
    
    try:
        proc = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode
        }
    except subprocess.TimeoutExpired:
        raise ValueError(f"Command timeout after {timeout}s")

def llama_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call local llama-server compatible endpoint.
    
    Args:
        args: {
            "model": str,
            "messages": list,
            "max_tokens": int,
            "temperature": float
        }
    
    Returns:
        LLM response JSON
    """
    import requests
    
    llama_url = os.environ.get("LLAMA_URL", "http://127.0.0.1:8001/v1/chat/completions")
    
    payload = {
        "model": args.get("model", "default"),
        "messages": args.get("messages", []),
        "max_tokens": args.get("max_tokens", 512),
        "temperature": args.get("temperature", 0.7),
    }
    
    timeout = TOOL_TIMEOUTS.get("llama", 60)
    
    try:
        resp = requests.post(llama_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise ValueError(f"LLM call failed: {str(e)}")

def file_read_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read small file from safe directory only.
    
    Args:
        args: {"path": "/data/safe/file.txt"}
    
    Returns:
        {"content": str, "size": int}
    """
    path = args.get("path")
    if not path:
        raise ValueError("missing 'path'")
    
    # Only allow reading from configured safe directory
    safe_root = os.environ.get("BRIDGE_SAFE_ROOT", "data/safe")
    abspath = os.path.abspath(path)
    safe_abs = os.path.abspath(safe_root)
    
    if not abspath.startswith(safe_abs + os.sep):
        raise ValueError(f"Path not in allowed root: {safe_root}")
    
    if not os.path.exists(abspath):
        raise ValueError(f"File not found: {path}")
    
    try:
        with open(abspath, "r", encoding="utf-8") as f:
            content = f.read(100000)  # Max 100KB
        return {"content": content, "size": len(content)}
    except Exception as e:
        raise ValueError(f"Read failed: {str(e)}")

# --- REGISTER EXAMPLE TOOLS ---
register_tool(
    "shell",
    shell_tool,
    allowlist={"cmds": ["ls", "du", "cat", "echo", "dir"]},
    timeout=10
)
register_tool("llama", llama_tool, timeout=60)
register_tool("file_read", file_read_tool, allowlist={}, timeout=10)

# --- MAIN EXECUTION ENDPOINT ---
@app.post("/call", response_model=ToolResult)
def call_tool(
    payload: ToolCall,
    api_key: str = Depends(require_scope("tool:call")),
    request: Request = None
):
    """
    Execute a registered tool with authorization and audit logging.
    
    Args:
        payload: Tool call request
        api_key: Validated API key
        request: FastAPI request object
    
    Returns:
        Tool execution result
    """
    tool_name = payload.tool_name
    request_id = payload.request_id or f"req-{int(time.time()*1000)}"
    
    if tool_name not in TOOLS:
        CALLS.labels(tool=tool_name, status="not_found").inc()
        audit_event({
            "event": "tool_not_found",
            "tool": tool_name,
            "request_id": request_id
        })
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    tool_fn = TOOLS[tool_name]

    # Optional per-tool scope enforcement
    if ENFORCE_PER_TOOL_SCOPE:
        per_tool_scope = f"tool:{tool_name}"
        rec = _get_token_record(api_key)
        scopes = rec.get("scopes", [])
        if per_tool_scope not in scopes and "admin" not in scopes:
            raise HTTPException(status_code=403, detail=f"Missing scope: {per_tool_scope}")
    start = time.time()
    
    try:
        # Audit pre-call
        audit_event({
            "event": "tool_call_start",
            "tool": tool_name,
            "request_id": request_id,
            "args": payload.args
        })
        
        # Execute with metrics
        with DURATION.labels(tool=tool_name).time():
            result = tool_fn(payload.args)
        
        CALLS.labels(tool=tool_name, status="ok").inc()
        
        # Audit success
        audit_event({
            "event": "tool_call_end",
            "tool": tool_name,
            "request_id": request_id,
            "result_summary": {"ok": True}
        })
        
        return ToolResult(ok=True, result=result)
        
    except Exception as e:
        CALLS.labels(tool=tool_name, status="error").inc()
        
        # Audit error
        audit_event({
            "event": "tool_call_error",
            "tool": tool_name,
            "request_id": request_id,
            "error": str(e)
        })
        
        logger.error(f"[{request_id}] Tool {tool_name} failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        duration = time.time() - start
        logger.info(f"[{request_id}] {tool_name} completed in {duration:.3f}s")

# --- HEALTH & METRICS ---
@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "ok": True,
        "version": "1.0.0",
        "tools_registered": len(TOOLS)
    }

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    data = generate_latest()
    return PlainTextResponse(
        data.decode("utf-8") if isinstance(data, bytes) else data,
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/tools")
def list_tools(api_key: str = Depends(require_scope("admin"))):
    """List registered tools (admin only)"""
    tools_info = []
    for name in TOOLS.keys():
        tools_info.append({
            "name": name,
            "timeout": TOOL_TIMEOUTS.get(name, DEFAULT_TIMEOUT),
            "allowlist": TOOL_ALLOWLIST.get(name, {})
        })
    return {"tools": tools_info}

@app.get("/audit/recent")
def get_recent_audit(
    limit: int = 50,
    api_key: str = Depends(require_scope("admin"))
):
    """Retrieve recent audit log entries (admin only)"""
    if not os.path.exists(AUDIT_LOG):
        return {"entries": []}
    
    with open(AUDIT_LOG, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    recent = lines[-limit:] if len(lines) > limit else lines
    entries = [json.loads(line.strip()) for line in recent if line.strip()]
    
    return {"entries": entries, "total": len(entries)}

@app.post("/admin/reload-keys")
def admin_reload_keys(api_key: str = Depends(require_scope("admin"))):
    """Reload keys from file at runtime."""
    _maybe_reload_keys()
    return {"ok": True, "keys": len(_KEYS_CACHE)}

@app.get("/admin/usage")
def admin_usage(api_key: str = Depends(require_scope("admin"))):
    """Get current usage counters (rpm window + daily)."""
    # Return shallow copy
    return {"daily": _DAILY_USAGE}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("BRIDGE_PORT", "8765"))
    uvicorn.run(app, host="0.0.0.0", port=port)

import functools
import time

_REGISTRY = {}

def action(name: str, timeout_s: int = 10):
    def wrap(fn):
        _REGISTRY[name] = {"fn": fn, "timeout": timeout_s}
        @functools.wraps(fn)
        def runner(*args, **kwargs):
            start = time.time()
            try:
                out = fn(*args, **kwargs)
                return {"ok": True, "name": name,
                        "latency_ms": int((time.time()-start)*1000),
                        "result": out}
            except Exception as e:
                return {"ok": False, "name": name, "error": repr(e),
                        "latency_ms": int((time.time()-start)*1000)}
        return runner
    return wrap

def get_action(name: str):
    return _REGISTRY[name]["fn"]

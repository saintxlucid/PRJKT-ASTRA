import ast, json, csv
from pathlib import Path

REPO_ROOT = Path(r"X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)")
API_DIR = REPO_ROOT / "src" / "astra" / "api"
OUT = REPO_ROOT / "ASTRA_API_ENDPOINTS.csv"

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}

rows = []

if API_DIR.exists():
    for p in API_DIR.rglob("*.py"):
        src = p.read_text(encoding="utf-8", errors="ignore")
        module = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        try:
            tree = ast.parse(src)
            for node in ast.walk(tree):
                # Look for @app.get(...) or @router.post(...) patterns
                if isinstance(node, ast.FunctionDef):
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Call):
                            method_name = None
                            if hasattr(dec.func, 'attr') and dec.func.attr.lower() in HTTP_METHODS:
                                method_name = dec.func.attr.upper()
                            path_arg = "?"
                            if dec.args and isinstance(dec.args[0], ast.Constant):
                                path_arg = dec.args[0].value
                            if method_name:
                                rows.append({
                                    "method": method_name,
                                    "path": path_arg,
                                    "handler": node.name,
                                    "module": module,
                                    "lineno": node.lineno,
                                    "rate_limit_hint": "Check astra_core.py or middleware for per-endpoint caps"
                                })
        except Exception as e:
            pass

with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["method", "path", "handler", "module", "lineno", "rate_limit_hint"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {OUT} ({len(rows)} endpoints discovered)")

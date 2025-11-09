import ast, json, sys
from pathlib import Path

REPO_ROOT = Path(r"X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)")
OUT = REPO_ROOT / "analysis" / "py_symbols.jsonl"
TARGETS = [
    "astra_core.py",
    "src/astra/api",
    "src/astra/core",
    "src/astra/rag",
    "src/astra/memory",
    "src/astra/infrastructure/llm",
    "src/astra/security",
    "src/astra/auth",
    "src/astra/visualization",
    "src/astra/task",
    "src/astra/daemon",
    "src/astra/executor",
]

OUT.parent.mkdir(exist_ok=True)

def list_py_files(root: Path):
    if root.is_file() and root.suffix == ".py":
        yield root
    elif root.is_dir():
        for p in root.rglob("*.py"):
            if "__pycache__" not in str(p):
                yield p

files_scanned = 0
with OUT.open("w", encoding="utf-8") as f:
    for t in TARGETS:
        p = REPO_ROOT / t
        if not p.exists():
            print(f"Target not found: {t}")
            continue
        for file in list_py_files(p):
            files_scanned += 1
            try:
                src = file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(src)
                data = {
                    "file": str(file.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "classes": [],
                    "functions": [],
                    "decorators": []
                }
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        data["classes"].append({
                            "name": node.name,
                            "lineno": node.lineno,
                            "end": getattr(node, 'end_lineno', node.lineno),
                            "bases": [ast.unparse(b) if hasattr(ast, 'unparse') else "?" for b in node.bases[:3]]
                        })
                    elif isinstance(node, ast.FunctionDef):
                        data["functions"].append({
                            "name": node.name,
                            "lineno": node.lineno,
                            "end": getattr(node, 'end_lineno', node.lineno),
                            "decorators": [ast.unparse(d) if hasattr(ast, 'unparse') else "?" for d in node.decorator_list[:3]]
                        })
                f.write(json.dumps(data) + "\n")
            except Exception as e:
                f.write(json.dumps({"file": str(file.relative_to(REPO_ROOT)).replace("\\", "/"), "error": str(e)}) + "\n")

print(f"Wrote {OUT} ({files_scanned} Python files scanned)")

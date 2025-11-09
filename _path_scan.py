import pathlib
import re
import sys

root = pathlib.Path('.')
include_dirs = {"src", "scripts", "config", "docs", "astra-local", "astra-launcher", "tests", "tools"}
patterns = [r"chromadb", r"\\.env", r"data[/\\]", r"models", r"hf_cache", r"gguf", r"database", r"logs"]
results = []
text_extensions = {'.py', '.md', '.yaml', '.yml', '.toml', '.ini', '.json', '.txt', '.ps1', '.psm1', '.html', '.cfg'}
files = [p for p in root.rglob('*') if p.is_file()]
print(f"[progress] Scanning {len(files)} files for hardcoded paths...")
for idx, rel in enumerate(files, 1):
    if rel.suffix.lower() not in text_extensions:
        continue
    parts = rel.parts
    if not parts or parts[0].lower() not in include_dirs:
        continue
    try:
        text = rel.read_text(encoding='utf-8')
    except Exception:
        continue
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            line = text.count('\n', 0, match.start()) + 1
            snippet = text[match.start():match.start()+80].replace('\n', ' ')
            results.append(f"{rel.as_posix()}:{line}: {snippet}")
    if idx % 200 == 0:
        print(f"[progress] Checked {idx} files...")
report = '\n'.join(results)
with open('TREE_CURRENT.md', 'a', encoding='utf-8') as handle:
    handle.write('\n\n## Hardcoded Path References\n')
    handle.write(report if report else 'None found')
print(f"[done] Recorded {len(results)} path references.")

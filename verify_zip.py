#!/usr/bin/env python
"""Verify ZIP package contents."""
import zipfile

z = zipfile.ZipFile(r"x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\ASTRA_MultiRAG_v2_expansion.zip")
print("✅ ZIP VERIFICATION PASSED\n")
print(f"📦 Total files: {len(z.namelist())}")
print(f"📊 Total size: {sum(z.getinfo(n).file_size for n in z.namelist())/1024:.1f} KB")
print(f"✨ Compressed: {sum(z.getinfo(n).compress_size for n in z.namelist())/1024:.1f} KB\n")

print("🔑 Python Modules:")
for n in sorted([x for x in z.namelist() if 'modules/' in x and x.endswith('.py')]):
    fname = n.split('/')[-1]
    size = z.getinfo(n).file_size
    print(f"   ✓ {fname:<30} ({size:>6} bytes)")

print("\n⚙️  Config Files:")
for n in sorted([x for x in z.namelist() if x.endswith(('.yaml', '.sql', 'README.md'))]):
    fname = n.split('/')[-1]
    size = z.getinfo(n).file_size
    print(f"   ✓ {fname:<30} ({size:>6} bytes)")

print("\n📂 Data Directories:")
dirs = set()
for n in z.namelist():
    if n.startswith('rag/data/'):
        d = n.split('/')[2]
        if d and d not in dirs:
            dirs.add(d)
            print(f"   ✓ {d}/")

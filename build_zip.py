#!/usr/bin/env python
"""
Create ASTRA Multi-RAG v2.0 expansion ZIP package
"""
import os
import zipfile
import pathlib

def create_zip():
    os.chdir(r"x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)")
    
    zip_path = 'ASTRA_MultiRAG_v2_expansion.zip'
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk('src/astra/rag'):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, 'src/astra')
                z.write(file_path, arcname)
    
    # Print summary
    with zipfile.ZipFile(zip_path, 'r') as z:
        files = z.namelist()
        print(f"✅ ZIP Created: {zip_path}")
        print(f"📦 Total Files: {len(files)}")
        print(f"\n🔑 Key Modules:")
        modules = [f for f in files if '/modules/' in f and f.endswith('.py')]
        for m in sorted(modules):
            print(f"   - {m}")
        print(f"\n⚙️  Config Files:")
        configs = [f for f in files if f.endswith(('.yaml', '.sql', 'README.md'))]
        for c in sorted(configs):
            print(f"   - {c}")

if __name__ == '__main__':
    create_zip()

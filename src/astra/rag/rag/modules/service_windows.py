"""
Windows-friendly polling watcher for ingestion.
Scans folder for new documents and auto-ingests them.
"""
import os
import time
import subprocess
import sys
import argparse
import pathlib


def scan_and_ingest(root: str, category: str, interval: int = 10):
    """Scan folder and ingest new/modified files."""
    seen = {}
    print(f"Watching: {root} (category: {category}, interval: {interval}s)")
    
    while True:
        for p in pathlib.Path(root).rglob('*'):
            if p.is_file():
                m = p.stat().st_mtime
                if str(p) not in seen or seen[str(p)] < m:
                    seen[str(p)] = m
                    print(f"New/modified: {p}")
                    subprocess.call([
                        sys.executable, 'ingest.py',
                        '--category', category,
                        '--path', str(p.parent)
                    ])
        
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description='File watcher for auto-ingestion')
    ap.add_argument('--root', required=True, help='Folder to watch')
    ap.add_argument('--category', required=True, help='Ingestion category')
    ap.add_argument('--interval', type=int, default=10, help='Scan interval (seconds)')
    args = ap.parse_args()
    
    scan_and_ingest(args.root, args.category, args.interval)


if __name__ == '__main__':
    main()

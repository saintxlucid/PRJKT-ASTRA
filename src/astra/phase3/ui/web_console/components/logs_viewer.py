"""Logs viewer component for web console (scaffold).

Provides utilities to tail logs and format them for the frontend.
"""
from collections.abc import Iterator


def tail_file(path: str) -> Iterator[str]:
    try:
        with open(path, encoding="utf-8") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    import time
                    time.sleep(0.1)
                    continue
                yield line
    except FileNotFoundError:
        return

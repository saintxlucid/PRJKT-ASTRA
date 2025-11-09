@echo off
REM Install development dependencies
pip install -r requirements-dev.txt

REM Install package in development mode
pip install -e .

REM Run tests to verify installation
pytest tests/test_gguf_io.py -v
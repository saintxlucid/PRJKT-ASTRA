@echo off
set ASTRA_EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
python -m uvicorn main:app --host 0.0.0.0 --port 8000

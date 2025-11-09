$env:ASTRA_EMBEDDINGS_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra_backend"
& "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000

@echo off
call .venv\Scripts\activate
uvicorn test_app:app --reload --port 8088
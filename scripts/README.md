# ASTRA Scripts

This directory contains utility scripts for managing the ASTRA project environment and testing its components.

## Activation Scripts

### Windows PowerShell
```powershell
.\scripts\activate_astra.ps1
```

**Features:**
- Activates local Python virtual environment (`.venv`)
- Sets PYTHONPATH to include project source
- Loads environment variables from `.env`
- Displays configuration and model information
- Shows available commands

### Windows Batch
```batch
scripts\activate_astra.bat
```

**Features:**
- Activates local virtual environment
- Sets PYTHONPATH
- Simpler alternative to PowerShell script

## Server Management

### Start ASTRA Server
```powershell
.\scripts\start_astra.ps1
```

**Features:**
- Activates environment
- Checks llama.cpp server availability
- Initializes database if needed
- Starts ASTRA server on port 8080

**Manual Start:**
```powershell
# After activating environment
poetry run python run_server.py
```

## Database Management

### Initialize Database
```powershell
python scripts\init_database.py
```

**Purpose:**
- Creates SQLite database at `data/database/astra.db`
- Initializes all required tables
- Run once during initial setup

**Location:** `X:\PROJECT_ASTRA\data\database\astra.db`

## Testing Scripts

### Test Model Information
```powershell
python scripts\test_model_info.py
```

**Tests:**
- Model information access via `get_model_info()`
- Direct access to GPT-OSS-20B and GPT-OSS-120B specs
- Architecture details (layers, experts, parameters)
- Reasoning modes (low/medium/high)
- Performance benchmarks
- Harmony format configuration
- Tool capabilities

**What it validates:**
- Pydantic models in `src/astra/models/model_info.py`
- Model registry functionality
- Pre-configured model objects

### Test Harmony Format
```powershell
python scripts\test_harmony.py
```

**Tests:**
- Harmony prompt building
- Multi-turn conversation formatting
- Response parsing
- Chain-of-thought (CoT) handling
- Channel support (analysis/commentary/final)
- Conversion to OpenAI format

**What it validates:**
- Harmony utilities in `src/astra/infrastructure/llm/harmony.py`
- Role hierarchy
- Special token handling
- Format conversion

### Check Dependencies
```powershell
python scripts\check_dependencies.py
```

**Tests:**
- Core packages (FastAPI, Pydantic, SQLAlchemy, ChromaDB)
- ML/AI packages (torch, transformers, sentence-transformers)
- Dev tools (pytest, black, ruff, mypy)

**What it validates:**
- All 120+ packages installed in `.venv/`
- Import functionality
- Package availability

## Quick Start

### First Time Setup

1. **Activate Environment:**
   ```powershell
   .\scripts\activate_astra.ps1
   ```

2. **Check Dependencies:**
   ```powershell
   python scripts\check_dependencies.py
   ```

3. **Initialize Database:**
   ```powershell
   python scripts\init_database.py
   ```

4. **Test Model Information:**
   ```powershell
   python scripts\test_model_info.py
   ```

5. **Test Harmony Format:**
   ```powershell
   python scripts\test_harmony.py
   ```

6. **Start Server:**
   ```powershell
   .\scripts\start_astra.ps1
   ```

### Daily Usage

```powershell
# Activate and start server
.\scripts\start_astra.ps1

# Or activate and run custom commands
.\scripts\activate_astra.ps1
poetry run python your_script.py
```

## Environment Configuration

All scripts use the persistent `.env` file at project root:

**Key Variables:**
- `ASTRA_DATABASE_URL` - Database connection (SQLite)
- `ASTRA_VECTOR_STORE_PERSIST_DIRECTORY` - ChromaDB location
- `ASTRA_LLM_MODEL_PATH` - Path to GGUF model file
- `ASTRA_LLM_REASONING_MODE` - Default reasoning mode (low/medium/high)
- `ASTRA_LLM_CONTEXT_LENGTH` - Max context (131,072 tokens)
- `ASTRA_LLM_USE_HARMONY_FORMAT` - Enable Harmony format (true)
- `PYTHONPATH` - Python import paths

**Absolute Paths:**
All paths in `.env` are absolute paths to `X:\PROJECT_ASTRA\` for persistence.

## Dependencies

### Virtual Environment
- Location: `X:\PROJECT_ASTRA\.venv\`
- Python: `.venv\Scripts\python.exe`
- Pip: `.venv\Scripts\pip.exe`
- Activation: `.venv\Scripts\Activate.ps1` (or `activate.bat`)

### Installed Packages (120+)
- **Web**: FastAPI 0.115.14, uvicorn 0.30.6, httpx 0.27.2
- **Data**: Pydantic 2.12.0, SQLAlchemy 2.0.43, ChromaDB 0.5.23
- **ML/AI**: torch 2.8.0, transformers 4.46.3, sentence-transformers 3.4.1
- **Utilities**: structlog 24.4.0, tenacity 9.1.2, python-dotenv 1.1.1
- **Dev**: pytest 8.4.2, black 24.10.0, ruff 0.7.4, mypy 1.18.2

View all packages:
```powershell
poetry show
```

## Model Intelligence

### GPT-OSS-20B Specifications
- **Total Parameters**: 20.9B
- **Active Parameters**: 3.6B per token
- **Layers**: 24
- **Experts**: 32 (top-4 selection)
- **Context**: 131,072 tokens
- **Quantization**: MXFP4 (4.25 bits per parameter)
- **Checkpoint Size**: 12.8 GiB
- **Tokenizer**: o200k_harmony (201,088 tokens)

### GPT-OSS-120B Specifications
- **Total Parameters**: 116.8B
- **Active Parameters**: 5.1B per token
- **Layers**: 36
- **Experts**: 128 (top-4 selection)
- **Context**: 131,072 tokens
- **Quantization**: MXFP4 (4.25 bits per parameter)
- **Checkpoint Size**: 60.8 GiB
- **Tokenizer**: o200k_harmony (201,088 tokens)

### Reasoning Modes
- **Low**: Fast responses, minimal CoT (~500 tokens, 1x cost)
- **Medium**: Balanced reasoning (~1,500 tokens, 1.5x cost)
- **High**: Deep analysis, extensive CoT (~5,000 tokens, 3x cost)

### Documentation
- **Model Card**: `docs/models/gpt_oss_model_card.md`
- **Quick Reference**: `docs/models/README.md`
- **Structured Models**: `src/astra/models/model_info.py`
- **Harmony Utilities**: `src/astra/infrastructure/llm/harmony.py`

## Troubleshooting

### Virtual Environment Not Activating
```powershell
# Verify venv exists
Test-Path .\.venv\Scripts\python.exe

# Re-create if needed
poetry install
```

### Database Errors
```powershell
# Re-initialize database
Remove-Item data\database\astra.db
python scripts\init_database.py
```

### Import Errors
```powershell
# Check PYTHONPATH
echo $env:PYTHONPATH

# Should be: X:\PROJECT_ASTRA\src;X:\PROJECT_ASTRA
```

### llama.cpp Server Not Running
```powershell
# Check if server is running
Invoke-WebRequest -Uri "http://localhost:8001/health" -Method GET

# Start manually if needed
# (See llama.cpp documentation)
```

## Additional Resources

- **Main README**: `../README.md`
- **Architecture**: `../ARCHITECTURE.md`
- **Installation**: `../INSTALLATION.md`
- **Configuration**: `../config/default.yaml`
- **Environment**: `../.env`

## Script Development

When creating new scripts:

1. **Add project root to path:**
   ```python
   import sys
   from pathlib import Path
   
   project_root = Path(__file__).parent.parent
   sys.path.insert(0, str(project_root / "src"))
   sys.path.insert(0, str(project_root))
   ```

2. **Use absolute imports:**
   ```python
   from src.astra.models.config import get_settings
   from src.astra.models.model_info import get_model_info
   ```

3. **Handle errors gracefully:**
   ```python
   if __name__ == "__main__":
       try:
           main()
           sys.exit(0)
       except Exception as e:
           print(f"Error: {e}", file=sys.stderr)
           sys.exit(1)
   ```

4. **Use local Python:**
   ```powershell
   .venv\Scripts\python.exe scripts\your_script.py
   ```

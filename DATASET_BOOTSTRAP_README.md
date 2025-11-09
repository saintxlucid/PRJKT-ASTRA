# ASTRA Dataset Bootstrap System

This directory contains a dataset bootstrap system for managing and validating datasets used by ASTRA subsystems (wake-word detection, ASR, NLU, safety evaluation, code generation, and Q&A).

## Quick Start

### 1. Setup Virtual Environment

**PowerShell (Windows)**:
```powershell
.\scripts\setup_venv.ps1
```

**Bash (Linux/macOS)**:
```bash
bash scripts/setup_venv.sh
```

### 2. Download Datasets

**PowerShell (Windows)**:
```powershell
.\scripts\pull_datasets.ps1
```

**Bash (Linux/macOS)**:
```bash
bash scripts/pull_datasets.sh
```

### 3. Validate Downloads

Run the verification script to ensure all datasets are downloaded and calculate their total size:

```bash
python scripts/verify_downloads.py
```

## Configuration

Edit `datasets.yaml` to customize datasets:

```yaml
cache_dir: "./cache"        # Hugging Face cache directory
output_dir: "./data"        # Local output directory for datasets

datasets:
  - name: <dataset-name>    # Dataset identifier (e.g., "squad")
    config: <config>        # Dataset configuration (optional)
    split: <split>          # Dataset split (e.g., "train[:5%]")
```

## Dataset Summary

The current dataset configuration includes:

| Dataset | Size | Purpose |
|---------|------|---------|
| wikitext | ~1.1 MB | Language modeling |
| imdb | ~4.9 MB | Sentiment analysis |
| snips_built_in_intents | ~0.0 MB | Intent classification |
| contemmcm/clinc150 | ~0.3 MB | Intent classification |
| ag_news | ~6.0 MB | News classification |
| docvqa/funsd | ~13.2 MB | Document understanding |
| allenai/real-toxicity-prompts | ~8.5 MB | Safety evaluation |
| mbpp | ~0.1 MB | Code generation |
| squad | ~4.0 MB | Question answering |

**Total Size**: ~38.1 MB

## Directory Structure

```
.
├── requirements.txt              # Python dependencies
├── datasets.yaml                 # Dataset configuration
├── DATASET_BOOTSTRAP_README.md   # This file
├── tools/
│   └── bootstrap_datasets.py     # Dataset downloader with retry logic
├── scripts/
│   ├── setup_venv.ps1           # Virtual environment setup (Windows)
│   ├── setup_venv.sh            # Virtual environment setup (Linux/macOS)
│   ├── pull_datasets.ps1        # Dataset pulling script (Windows)
│   ├── pull_datasets.sh         # Dataset pulling script (Linux/macOS)
│   └── verify_downloads.py      # Download validation and size calculation
├── data/                         # Downloaded datasets (auto-created)
│   ├── wikitext/
│   ├── imdb/
│   ├── snips_built_in_intents/
│   ├── contemmcm__clinc150/
│   ├── ag_news/
│   ├── docvqa__funsd/
│   ├── allenai__real-toxicity-prompts/
│   ├── mbpp/
│   ├── squad/
│   └── _manifest.json           # Dataset manifest
└── cache/                        # Hugging Face cache (auto-created)
```

## Privacy & Usage Notes

### Data Usage
- All datasets are sourced from the Hugging Face Hub and are subject to their respective licenses.
- Ensure compliance with dataset licenses before using datasets in production.

### Caching
- The `cache/` directory stores downloaded data for reproducibility.
- The `data/` directory contains extracted and processed datasets ready for use.

### Slicing
- Datasets are sliced (e.g., `train[:10%]`) to reduce storage footprint and improve download times.
- Adjust slice sizes in `datasets.yaml` for different use cases.

### Network Requirements
- Initial download requires approximately **50 MB** of network bandwidth.
- Subsequent runs use local cache and do not require network access.

## Troubleshooting

### Script Errors

If you encounter errors during dataset download:

1. **Retry manually**:
   ```bash
   python tools/bootstrap_datasets.py
   ```

2. **Clear cache and retry**:
   ```bash
   rm -rf cache/  # Linux/macOS
   rmdir /s cache # Windows
   python tools/bootstrap_datasets.py
   ```

3. **Check internet connectivity**:
   - Ensure you have a stable internet connection.
   - Try downloading a single dataset first by editing `datasets.yaml`.

### Missing Manifest

If `verify_downloads.py` reports "No manifest found":

1. Run the bootstrap script to generate the manifest:
   ```bash
   python tools/bootstrap_datasets.py
   ```

2. Then validate:
   ```bash
   python scripts/verify_downloads.py
   ```

## Support

For issues or questions, refer to:
- [Hugging Face Datasets Documentation](https://huggingface.co/docs/datasets)
- [ASTRA Project Documentation](../README.md)

# Info & Data Extraction + GGUF Ingestion Module

This add-on gives you:
1) **Document → Prompt dataset** builder (extract, clean, chunk) in `ingestion/`
2) **GGUF metadata writer** in `gguf_tools/` so you can stamp your distilled model with data + provenance.

## 1) Build a prompt dataset from documents
```bash
pip install pdfminer.six python-docx beautifulsoup4 transformers pyyaml
python -m ingestion.build_dataset \
  --src ./my_docs \
  --out_jsonl artifacts/datasets/raw_chunks.jsonl \
  --student_tokenizer gpt2 \
  --max_tokens 512 --overlap 32
```

This writes JSONL rows like:
```json
{"doc_id":"abcd1234","chunk_id":0,"source_path":"my_docs/foo.pdf","prompt":"...","neox_output":""}
```

Feed that to your teacher generator to fill neox_output, then train.

## 2) Update GGUF metadata with dataset provenance

Install the gguf python tooling from llama.cpp (same environment you use to convert to GGUF). Then:
```bash
python -m gguf_tools.update_metadata \
  --in_gguf models/gpt2-distilled.gguf \
  --out_gguf models/gpt2-distilled.withmeta.gguf \
  --set general.name=GPT2-Distilled-NeoX20B \
  --set distillation.teacher=GPT-NeoX-20B \
  --set distillation.temperature=2.0 \
  --dataset_jsonl artifacts/datasets/final_train.jsonl
```

The output GGUF will include keys like:
- `training.dataset_path`
- `training.dataset_sha256`
- `training.dataset_rows`

plus any custom `--set key=value` you pass.

## 3) Convert merged HF model → GGUF (wrapper)

Use `gguf_tools/to_gguf_stub.py` as a convenience wrapper around llama.cpp's `convert-hf-to-gguf.py`:
```bash
python -m gguf_tools.to_gguf_stub \
  --hf_model_path models/gpt2-distilled-merged \
  --out_dir models/gguf_out \
  --convert_script /path/to/llama.cpp/convert-hf-to-gguf.py \
  --quant Q4_K_M
```

**Note:** GGUF is for model weights + metadata. It is not a container for your whole dataset. Keep datasets as sidecars (JSONL/Parquet), and embed only provenance & stats in GGUF.
# Makefile for GPT-2 Knowledge Distillation

# Default target
.PHONY: help
help:
	@echo "GPT-2 Knowledge Distillation Makefile"
	@echo "====================================="
	@echo "Available targets:"
	@echo "  setup          - Install dependencies"
	@echo "  distill        - Run phase B distillation with KD+CE"
	@echo "  eval           - Run evaluation harness"
	@echo "  docker-build   - Build Docker image"
	@echo "  docker-run     - Run Docker container"
	@echo "  clean          - Clean artifacts"

# Setup environment
.PHONY: setup
setup:
	pip install -r requirements.txt

# Run phase B distillation
.PHONY: distill
distill:
	python scripts/train_gpt2_distilled.py --config configs/run_phaseB.yaml

# Run evaluation
.PHONY: eval
eval:
	bash eval/run_harness.sh

# Build Docker image
.PHONY: docker-build
docker-build:
	docker build -t gpt2-distillation .

# Run Docker container
.PHONY: docker-run
docker-run:
	docker run --gpus all -it --rm \
		-v $(PWD):/workspace \
		-v ~/.cache/huggingface:/root/.cache/huggingface \
		gpt2-distillation

# Clean artifacts
.PHONY: clean
clean:
	rm -rf artifacts/*
	rm -rf models/*
	rm -rf logs/*

# Data preprocessing
.PHONY: preprocess
preprocess:
	python scripts/data_scoring.py \
		--input_dataset data/raw_dataset.jsonl \
		--output_dataset data/scored_dataset.jsonl \
		--hard_set data/hard.jsonl
	python scripts/data_filter.py \
		--input_dataset data/scored_dataset.jsonl \
		--output_dataset data/filtered_dataset.jsonl

# Tokenizer audit
.PHONY: audit
audit:
	python scripts/token_map_audit.py \
		--teacher artifacts/logits/train_teacher_topk100.jsonl \
		--student gpt2-large

# Quick test
.PHONY: test
test:
	python -m pytest tests/ -v

# Format code
.PHONY: format
format:
	black .
	isort .

# Lint code
.PHONY: lint
lint:
	flake8 .
	pylint scripts/ training/ eval/

# Generate documentation
.PHONY: docs
docs:
	pdoc --html --output-dir docs scripts/ training/ eval/
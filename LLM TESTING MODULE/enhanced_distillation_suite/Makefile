.PHONY: phaseA phaseB phaseC eval merge ppl sanity

phaseA:
	accelerate launch --config_file configs/accelerate.yaml scripts/train_gpt2_distilled.py --config configs/run_phaseA.yaml
phaseB:
	python scripts/train_gpt2_distilled.py --config configs/run_phaseB.yaml
phaseC:
	python scripts/train_gpt2_distilled.py --config configs/run_phaseC.yaml
eval:
	bash eval/run_harness.sh models/phaseC
merge:
	python scripts/merge_lora.py --base gpt2-large --lora_path models/phaseC --out models/gpt2-distilled-merged
ppl:
	python eval/ppl_latency.py --model models/phaseC
sanity:
	python scripts/generate_neox_outputs.py --prompts data/general.jsonl \
	  --server vllm --host http://127.0.0.1:8000 --emit-logits --topk 100 \
	  --out artifacts/logits/topk100.jsonl
	python scripts/data_scoring.py --in_jsonl artifacts/logits/topk100.jsonl \
	  --out_jsonl artifacts/logits/topk100_scored.jsonl
	make phaseA && make phaseB && make phaseC
	make eval
	make ppl
	make merge
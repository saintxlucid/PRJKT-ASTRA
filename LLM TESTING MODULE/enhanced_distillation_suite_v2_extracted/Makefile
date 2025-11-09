.PHONY: phaseA phaseB phaseC eval

phaseA:
	accelerate launch --config_file configs/accelerate.yaml scripts/train_gpt2_distilled.py --config configs/run_phaseA.yaml
phaseB:
	python scripts/train_gpt2_distilled.py --config configs/run_phaseB.yaml
phaseC:
	python scripts/train_gpt2_distilled.py --config configs/run_phaseC.yaml
eval:
	bash eval/run_harness.sh
.PHONY: run-api test

run-api:
	python -m src.astra.api.toolbus

test:
	pytest -q

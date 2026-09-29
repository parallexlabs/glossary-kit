.PHONY: demo install test lint typecheck clean

PYTHON ?= python3
PIP := $(PYTHON) -m pip
GLOSSARY_KIT := $(if $(wildcard .venv/bin/glossary-kit),.venv/bin/glossary-kit,glossary-kit)

install:
	$(PIP) install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check src tests

typecheck:
	mypy src/glossary_kit
	pyright src/glossary_kit

demo:
	mkdir -p examples/output
	$(GLOSSARY_KIT) validate examples/sample_glossary.yaml
	$(GLOSSARY_KIT) lint examples/sample_glossary.yaml
	$(GLOSSARY_KIT) export skos examples/sample_glossary.yaml -o examples/output/glossary.ttl
	$(GLOSSARY_KIT) export jsonld examples/sample_glossary.yaml -o examples/output/glossary.jsonld
	$(GLOSSARY_KIT) export csv examples/sample_glossary.yaml -o examples/output/glossary.csv
	$(GLOSSARY_KIT) export site examples/sample_glossary.yaml -o examples/output/site
	$(GLOSSARY_KIT) assess examples/sample_glossary.yaml -o examples/output/maturity.html
	$(GLOSSARY_KIT) templates -o examples/output/governance
	@echo "Demo outputs written to examples/output/"

clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

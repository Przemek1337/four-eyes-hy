PYTHON ?= python3
.PHONY: install test run bench ui smoke demo-docs
install:
	$(PYTHON) -m pip install -e '.[dev,harness]'
test:
	$(PYTHON) -m pytest
run:
	$(PYTHON) -m foureyes.cli serve --policy policy.yaml --harness kyc
bench:
	$(PYTHON) scripts/bench.py
ui:
	cd ui && npm install && npm run build
smoke:
	cd ui && node scripts/smoke.mjs
demo-docs:
	$(PYTHON) -m harness.demo_documents.generate_registry_extract_pdfs

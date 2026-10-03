PYTHON ?= python3
.PHONY: install test run bench
install:
	$(PYTHON) -m pip install -e '.[dev]'
test:
	$(PYTHON) -m pytest
run:
	$(PYTHON) -m foureyes.cli serve --policy policy.yaml --harness kyc
bench:
	$(PYTHON) scripts/bench.py

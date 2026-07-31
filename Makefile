# Optional convenience targets for a personal Linux machine.

PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
ASURITE ?= your_asurite

export MPLBACKEND := Agg

.PHONY: venv install doctor examples rule-smoke replay-smoke submission

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(BIN)/pip install --upgrade pip "setuptools>=68"
	$(BIN)/pip install -e .

doctor:
	$(BIN)/python -m agentic_driving_coach doctor

examples:
	$(BIN)/python examples/01_hello_reactor.py
	$(BIN)/python examples/02_timer_and_ports.py
	$(BIN)/python examples/03_logical_delay.py
	$(BIN)/python examples/04_deadline_lag.py

rule-smoke:
	$(BIN)/python -m agentic_driving_coach run --scenario stop-sign --driver beginner \
		--coach rule --fast --output results/rule-smoke

replay-smoke:
	$(BIN)/python -m agentic_driving_coach run --scenario stop-sign --driver beginner \
		--coach replay --trace data/replay/example_trace.jsonl --fast \
		--output results/replay-smoke

submission:
	$(BIN)/python scripts/make_submission.py --asurite $(ASURITE)

# CARS-SF developer entry points. Mininet targets need root and the venv interpreter.
PY ?= .venv/bin/python
SUDO ?= sudo
SCENARIO ?= normal
DURATION ?= 30

.PHONY: setup data models test integration regression experiment clean-net handbook pipeline

setup:            ## create the venv (system site-packages expose Mininet) and install deps
	test -x $(PY) || python3 -m venv --system-site-packages .venv
	$(PY) -m pip install -r requirements.txt

SEED ?= 42

data:             ## regenerate the seeded, contract-validated RSNSD synthetic dataset (gitignored, ~85 MB)
	$(PY) -m dataset.rsnsd --per-scenario 6000 --seed $(SEED)

models:           ## train SliceNet baseline + RL scheduler (CEM + PPO, seeds 0 1 2)
	$(PY) experiments/run_slicenet_pipeline.py --baseline-only
	$(PY) scheduler/train.py --algo all --seeds 0 1 2

test:             ## unit tests
	$(PY) -m pytest

integration:      ## end-to-end runs on an emulated network, no sudo (user namespaces)
	$(PY) -m pytest -m integration

regression: test integration

MODE ?= synthetic
pipeline:         ## end-to-end pipeline: make pipeline MODE=unit|synthetic|mininet|rl|full
	$(PY) run_pipeline.py --mode $(MODE)

experiment:       ## real Open vSwitch run: make experiment SCENARIO=fiber_cut DURATION=30
	$(SUDO) $(PY) run_experiment.py --scenario $(SCENARIO) --duration $(DURATION) --apply-qos

clean-net:        ## remove Mininet leftovers after a crashed run
	$(SUDO) mn -c

handbook:         ## regenerate numbers from results and build the defense handbook PDF
	$(PY) experiments/defense_numbers.py
	cd docs/defense && pdflatex -interaction=nonstopmode handbook.tex >/dev/null && pdflatex -interaction=nonstopmode handbook.tex >/dev/null

ifeq ($(OS),Windows_NT)
VENV_PY := .venv/Scripts/python.exe
else
VENV_PY := .venv/bin/python
endif

PYTHON ?= python

.PHONY: setup seed test lint typecheck web-lint web-typecheck dev build-web screenshots verify clean

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r requirements.txt -r requirements-dev.txt
	npm --prefix web install

seed:
	$(VENV_PY) api/scripts/seed_demo.py

test:
	$(VENV_PY) -m pytest --cov=app --cov-report=term-missing

lint:
	$(VENV_PY) -m ruff check api
	$(VENV_PY) -m ruff format --check api

typecheck:
	$(VENV_PY) -m mypy

web-lint:
	npm --prefix web run lint

web-typecheck:
	npm --prefix web run typecheck

dev:
	$(VENV_PY) api/scripts/dev.py

build-web:
	npm --prefix web run build

screenshots:
	node web/scripts/screenshots.mjs

verify: lint typecheck test web-lint web-typecheck

clean:
	$(VENV_PY) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache','.mypy_cache','.ruff_cache','web/.next']]"

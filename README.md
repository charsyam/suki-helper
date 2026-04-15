# suki-helper

Desktop PDF search application with:

- Python desktop UI
- per-PDF SQLite index databases
- whitespace-insensitive 2-gram search
- order-aware ranking

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run

```bash
source .venv/bin/activate
python -m suki_helper.app.main
```

## Benchmark

```bash
source .venv/bin/activate
PYTHONPATH=src python -m suki_helper.tools.benchmark_search /path/to/file.pdf "search query"
```

## Status

This repository is in early MVP scaffolding.

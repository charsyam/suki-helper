# suki-helper

Desktop PDF search application with:

- Python desktop UI
- per-PDF SQLite index databases
- whitespace-insensitive 2-gram search
- order-aware ranking
- Windows single-file packaging path

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

For Windows packaging:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[build]
```

## Run

```bash
source .venv/bin/activate
python -m suki_helper.app.main
```

Application data is stored in the per-user app data directory by default.

- macOS: `~/Library/Application Support/suki-helper/data`
- Linux: `~/.local/share/suki-helper/data`
- Windows: `%APPDATA%\charsyam\suki-helper\data`

If needed, override the storage root with `SUKI_HELPER_ROOT`.

## Benchmark

```bash
source .venv/bin/activate
PYTHONPATH=src python -m suki_helper.tools.benchmark_search /path/to/file.pdf "search query"
```

## Windows EXE Build

On Windows:

```bat
tools\build_windows_exe.bat
```

Output:

```text
dist\suki-helper.exe
```

## Status

This repository is in early MVP scaffolding.

# Progress Log

## Current Baseline

Last stable commit before this log update:

- `95949bb` - `Initialize project scaffolding and search foundation`

Current working state after that commit:

- search service implemented
- order-aware ranking implemented
- snippet extraction implemented
- document registration and per-PDF indexing connected to the UI
- empty-state-first startup flow implemented
- `File -> Add PDF` menu and add button implemented
- right-pane PDF page rendering implemented
- left-pane result thumbnail generation implemented
- background worker support added for PDF indexing and right-pane page rendering
- right-pane zoom and fit controls added
- visible-row lazy thumbnail loading added
- benchmark script added for indexing and search timing
- rarity-aware ranking signal added
- explicit no-results empty state added to the left pane

## Implemented So Far

### Foundation

- Python project scaffold created
- `.venv`-based workflow established
- PySide6 app shell added
- Git repository initialized

### Storage

- `catalog.db` bootstrap implemented
- per-PDF index DB bootstrap implemented
- `index_key` generation implemented
- page and gram posting persistence implemented

### Search Core

- PDF page text extraction implemented with `PyMuPDF`
- whitespace-insensitive normalization implemented
- normalized-to-original offset mapping implemented
- 2-gram tokenization and page posting generation implemented
- selected-PDF-only search implemented
- exact compact-match verification implemented
- order-aware ranking implemented
- page-frequency-based rarity weighting implemented
- snippet/context extraction implemented

### UI

- startup empty state implemented
- PDF add flow implemented
- indexed PDF selection implemented
- Enter-based search connected
- result list connected
- result click renders the selected page as an image in the right pane
- result list items include basic page thumbnails
- indexing and right-pane page rendering now run through worker tasks
- right-pane supports `Fit Width`, `Actual Size`, `Zoom In`, and `Zoom Out`
- thumbnails are generated lazily for visible result rows
- left pane shows an explicit no-results state when a search returns zero matches

## Verified State

Verification command:

```bash
source .venv/bin/activate
PYTHONPATH=src pytest -q
```

Latest verified result at the time of writing:

- `19 passed`

App launch command:

```bash
cd /Users/daemyung/develop/charsyam/suki-helper
source .venv/bin/activate
PYTHONPATH=src python -m suki_helper.app.main
```

## Known Gaps

- right pane does not yet render high-resolution page images
- indexing has a worker-based UI path, but broader job orchestration is still minimal
- thumbnail generation still runs on the UI thread for visible rows
- performance tuning and Windows validation are still pending
- benchmark coverage is still basic and does not yet compare multiple document sizes
- repeated text that appears on almost every page can still dominate when the query itself is globally repeated

## Next Recommended Start Point

Resume from:

1. benchmark larger PDFs and tune cache and worker behavior
2. move visible-row thumbnail generation off the UI thread safely
3. add a more explicit indexing progress UI
4. validate the current flow on Windows

## Rule For Future Updates

When a feature phase is completed:

- update `work_plan.md` status for the relevant phase
- append or revise `progress.md` so the next session can resume from the new baseline

# MVP Work Plan

## 1. Goal

This document defines the implementation order for the MVP based on technical dependencies, not just feature grouping.

The priority is:

1. establish a stable application skeleton
2. implement the search core that determines correctness and performance
3. connect UI and rendering around that core

## 2. Dependency Principles

The following dependency rules drive the order:

- UI widgets should not be built deeply before service interfaces exist
- search ranking should not be implemented before normalization and indexing are stable
- rendering and thumbnails should not be optimized before result selection flow exists
- SQLite schema and storage rules should be fixed before indexing workers are finalized
- benchmark work should begin as soon as the first end-to-end search path exists

## 3. Critical Path

The critical path for a usable MVP is:

1. repository and runtime skeleton
2. storage foundation
3. PDF extraction
4. text normalization and offset mapping
5. 2-gram indexing
6. selected-PDF search flow
7. ranking and exact verification
8. snippet generation
9. result list UI
10. thumbnail rendering
11. high-resolution detail rendering
12. performance validation

If any of steps 2 through 8 are weak, the UI will look complete but the product will still not work well. That is why search-core tasks are earlier than most UI polish.

## 4. Ordered Work Breakdown

### Phase 0. Repository Foundation

Status:

- completed

Objective:

- create a stable development baseline

Tasks:

- initialize Git repository
- add `.gitignore`
- define Python version target
- create initial directory structure under `src/` and `tests/`
- add dependency manifest such as `pyproject.toml`
- document basic run command

Depends on:

- none

Blocks:

- all implementation work

Parallelizable:

- very limited

Exit criteria:

- app can be launched as an empty shell
- dependencies install cleanly on the target environment

### Phase 1. Application Skeleton

Status:

- completed

Objective:

- establish the basic desktop app structure and service boundaries

Tasks:

- create `main.py` bootstrap
- create main window with left and right panes
- add placeholders for PDF selector, search input, result list, and page viewer
- define service interfaces for document registry, indexing, search, and rendering
- set up signal or callback flow between UI and services

Depends on:

- Phase 0

Blocks:

- all meaningful UI integration

Parallelizable:

- widget skeleton and service interface definitions can be done in parallel after app bootstrap exists

Exit criteria:

- window launches
- Enter action from the search field reaches the search service boundary
- PDF selection UI placeholder exists

### Phase 2. Storage Foundation

Status:

- completed

Objective:

- establish persistent storage for PDF registration and per-PDF index data

Tasks:

- implement `catalog.db` creation and migration
- implement per-PDF index DB creation logic
- define `index_key` generation rule
- implement repository layer for `documents` catalog table
- implement repository layer for per-PDF `pages` and `gram_postings`
- define SQLite pragmas and connection lifecycle

Depends on:

- Phase 0

Blocks:

- indexing
- search persistence
- cached reopen flow

Parallelizable:

- catalog repository and per-PDF repository work can proceed in parallel once schema is fixed

Exit criteria:

- app can register a PDF in `catalog.db`
- app can create and open a per-PDF index DB

### Phase 3. PDF Extraction Core

Status:

- completed

Objective:

- extract reliable page-level text and page metadata

Tasks:

- implement PDF open and page iteration with `PyMuPDF`
- extract page text
- capture page count and page number metadata
- define extraction error handling
- add extraction smoke tests with sample PDFs

Depends on:

- Phase 0
- Phase 2 for persistence target

Blocks:

- normalization
- indexing
- any real search result

Parallelizable:

- extraction tests can be written alongside extractor implementation

Exit criteria:

- extracted page text can be stored in the per-PDF index DB

### Phase 4. Normalization and Offset Mapping

Status:

- completed

Objective:

- produce deterministic searchable text and reversible position mapping

Tasks:

- implement Unicode normalization policy
- remove whitespace for search text
- preserve original text separately
- generate `norm_to_original_map`
- add unit tests for Korean and mixed text examples

Depends on:

- Phase 3

Blocks:

- 2-gram index generation
- exact verification
- snippet extraction

Parallelizable:

- tests can run in parallel with implementation

Exit criteria:

- normalized text and offset mapping are reproducible and verified by tests

### Phase 5. 2-Gram Index Construction

Status:

- completed

Objective:

- build the fast candidate retrieval layer

Tasks:

- implement 2-gram tokenizer
- generate gram postings per page
- persist postings into per-PDF index DB
- special-case short queries for direct scan fallback
- add candidate retrieval unit tests

Depends on:

- Phase 2
- Phase 4

Blocks:

- fast search
- performance validation

Parallelizable:

- tokenizer tests and posting persistence tests can be split

Exit criteria:

- a selected PDF can return candidate page ids from query grams

### Phase 6. Search Core

Status:

- completed

Objective:

- make query execution correct and fast enough for the MVP

Tasks:

- implement selected-PDF-only query execution
- open or reuse the correct per-PDF DB on search
- retrieve candidate pages from gram postings
- load candidate page texts
- perform exact normalized substring verification
- add one-character and empty-query handling

Depends on:

- Phase 5

Blocks:

- ranking
- snippets
- UI search results

Parallelizable:

- DB access path optimization and verification logic can be developed side by side once candidate retrieval exists

Exit criteria:

- Enter on a selected PDF returns a verified list of matching pages

### Phase 7. Ranking and Snippet Logic

Status:

- completed

Objective:

- improve search quality to match the product expectations

Tasks:

- implement ordered token extraction from query input
- implement order-aware match classification
- score compact, separator-adjacent, ordered-near, and unordered matches
- generate display snippets from original text
- add ranking tests for `해외 동포` style cases

Depends on:

- Phase 4
- Phase 6

Blocks:

- trustworthy result ordering
- useful result display

Parallelizable:

- snippet extraction and ranking implementation can be done separately after verified matches exist

Exit criteria:

- ranking places order-preserving results above reversed-order results
- each result contains readable context text

### Phase 8. PDF Registration and Indexing Workflow

Status:

- completed for local indexing flow
- background indexing worker added for the current UI path
- explicit indexing progress UI added

Objective:

- connect PDF loading to background indexing and catalog updates

Tasks:

- implement document registry service
- add background indexing worker
- update catalog status during indexing
- show index-ready PDFs in selector
- add reindex decision based on file size and mtime changes

Depends on:

- Phase 2
- Phase 3
- Phase 4
- Phase 5

Blocks:

- practical multi-PDF usage

Parallelizable:

- worker plumbing and catalog status UI can proceed together once indexing APIs exist

Exit criteria:

- user can load PDFs and later select an indexed one for search

### Phase 9. Result List UI

Status:

- completed for initial searchable UI

Objective:

- expose the search engine through a usable result list

Tasks:

- bind Enter in search input to the search service
- render result rows with page number and snippet
- display result count
- handle row selection
- preserve selected result state

Depends on:

- Phase 1
- Phase 6
- Phase 7
- Phase 8

Blocks:

- thumbnail-driven usability
- detail view workflow

Parallelizable:

- result item widget styling and result list data model can be split

Exit criteria:

- user can search one selected PDF and click a result row

### Phase 10. Thumbnail Pipeline

Status:

- completed for initial synchronous thumbnail rendering
- visible-row lazy thumbnail loading added

Objective:

- render low-resolution page previews efficiently

Tasks:

- implement thumbnail render worker
- lazy-load thumbnails for visible rows only
- add memory and disk cache
- connect thumbnails to result rows

Depends on:

- Phase 3
- Phase 8
- Phase 9

Blocks:

- complete left-pane experience

Parallelizable:

- cache implementation and UI binding can proceed in parallel after render API exists

Exit criteria:

- visible result rows display thumbnails without blocking the UI

### Phase 11. Detail Viewer Pipeline

Status:

- completed for initial synchronous page rendering
- background page-render worker added for the current UI path

Objective:

- show high-resolution page image for the clicked result

Tasks:

- implement detail render worker
- add fit-to-view rendering path
- wire row click to page render request
- cache high-resolution images

Depends on:

- Phase 3
- Phase 9

Blocks:

- full MVP workflow completion

Parallelizable:

- viewer widget behavior and render cache work can be split

Exit criteria:

- clicking a result shows the correct page image in the right pane

### Phase 12. Performance and Reliability Pass

Status:

- in progress
- baseline benchmark script added
- rarity-aware ranking signal added to reduce repeated-text dominance
- initial Windows single-file packaging path defined

Objective:

- confirm the architecture actually meets the product goal

Tasks:

- benchmark indexing time on 100 to 200+ page PDFs
- benchmark query latency on indexed PDFs
- inspect candidate counts and ranking cost
- tune SQLite pragmas and connection reuse
- tune thumbnail caching and render DPI
- validate on Windows
- verify the PyInstaller one-file build on a real Windows machine

Depends on:

- Phase 6 through Phase 11

Blocks:

- release readiness

Parallelizable:

- performance profiling and bug fixing can proceed together

Exit criteria:

- query latency and UI responsiveness are acceptable on representative PDFs

## 5. Dependency Graph Summary

### Hard Dependencies

- Phase 0 -> Phase 1, 2
- Phase 2 -> Phase 3, 5, 8
- Phase 3 -> Phase 4, 10, 11
- Phase 4 -> Phase 5, 7
- Phase 5 -> Phase 6
- Phase 6 -> Phase 7, 9
- Phase 7 -> Phase 9
- Phase 8 -> Phase 9, 10
- Phase 9 -> Phase 10, 11
- Phase 10 and 11 -> Phase 12

### Practical Critical Path

- Phase 0
- Phase 2
- Phase 3
- Phase 4
- Phase 5
- Phase 6
- Phase 7
- Phase 8
- Phase 9
- Phase 11
- Phase 12

Thumbnail work is important, but the right-pane detail flow is slightly more critical because it completes the main result-click experience.

## 6. Recommended Immediate Next Steps

The next three tasks should be:

1. add background workers so indexing and rendering do not block the UI
2. replace eager thumbnail generation with lazy visible-row rendering
3. add zoom and fit controls to the right-pane image viewer

Completed since the last checkpoint:

- background indexing and right-pane render workers added
- right-pane `Fit Width`, `Actual Size`, `Zoom In`, and `Zoom Out` controls added
- result thumbnails now load lazily for visible rows
- benchmark entry point added for indexing and search timing
- page-frequency-based rarity weighting added to ranking
- indexing progress label and progress bar added

Reason:

- these tasks unlock the entire search core
- they avoid premature UI work
- they reduce the risk of redesigning storage after UI code is already written

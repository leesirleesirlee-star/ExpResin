# ExpResin

AI-assisted digitalization pipeline for ion-exchange resin experiments (AI4S).
From raw Excel workbooks to structured experiment archives and template-based
Excel exports — **recognize → canonicalize → archive → export**.

## Repository Layout

| Path | Description |
|---|---|
| `expresin-pipeline/` | FastAPI backend + core Python pipeline: L1/L2 table recognition, canonical long-table materialization, derived-quantity computation, template fill/export |
| `expresin-portal/` | Vue 3 + Vite frontend workbench: experiment setup, recognition review, experiment archive, API docs |
| `docs/` | Living documents: `ExpResin-PRD.md`, `ExpResin-UI-Design-Spec-v1.0.md`, `ExpResin-Project-Roadmap-v2.0.md`, `design-changelog.md`, `research-opportunities.md`, `benchmark-v0.md` |
| `docs/session-logs/` | Per-session progress logs (append-only history) |
| `materials/template-drafts/` | Original experiment template drafts from the advisor (transcribed into JSON configs under `expresin-pipeline/config/templates/`) |
| `materials/guides/` | Research proposal and build/implementation guide documents (docx) |
| `materials/data/` | Original raw data workbooks (xlsx) used by benchmark and pipeline scripts |

## Features

- **Table recognition**: header detection, block segmentation, column mapping
  with confidence scores; human review before archiving.
- **Canonical long table**: data values are always re-read from the raw workbook
  (`data_only=True`), never stitched from recognition snapshots.
- **Template export**: one-click Excel export per experiment type
  (batch / column / electrochemical) via
  `GET /v1/experiments/{id}/export/template`; canonical CSV export included.
- **Derived quantities**: batch (Ce, removal %, qe, equilibrium time),
  column (treated volume, BV, Ct/C0, breakthrough/exhaustion),
  electrochemical (current density, charge passed, energy consumption) —
  every derived value carries an explicit `method`; uncomputable inputs yield
  a `reason`, never a fabricated number.

## Quick Start

### Backend (port 8000)

```bash
cd expresin-pipeline
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r server/requirements.txt
copy .env.example .env   # fill in your DeepSeek API key
python -m uvicorn app:app --app-dir server --port 8000
```

### Frontend (port 5173)

```bash
cd expresin-portal
npm install
npm run dev
```

Open http://localhost:5173/ — the archive detail page of any archived
experiment offers **Export Template Excel** and **Export CSV**.

## API Overview

- `POST /v1/sessions` · `POST /v1/ingest` · `POST /v1/recognize`
- `GET  /v1/experiments` · `GET /v1/experiments/{id}`
- `GET  /v1/experiments/{id}/data/canonical[.csv|.json]`
- `POST /v1/experiments/{id}/archive`
- `GET  /v1/experiments/{id}/export/template`

The full endpoint specification lives in `docs/` and the in-app API Docs page.

## Status

Active development. Design decisions are recorded in
`docs/design-changelog.md`; per-session progress in `docs/session-logs/`.
This README evolves with the project.

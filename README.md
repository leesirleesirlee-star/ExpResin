# ExpResin

AI-assisted digitalization pipeline for ion-exchange resin experiments (AI4S).
From raw Excel workbooks to structured experiment archives and template-based
Excel exports — **recognize → canonicalize → archive → export**.

This repository ships **source code and documents only**. Real experiment
workbooks, recognition caches, the local archive database and session uploads
stay on the machine that produced them (see
[Data & Local Files](#data--local-files-not-published)).

## Repository Layout

| Path | Description |
|---|---|
| `expresin-pipeline/` | FastAPI backend + core Python pipeline: L1/L2 table recognition, canonical long-table materialization, derived-quantity computation, record-template fill/export, user auth (`server/auth.py`), NAS publishing (`src/nas_adapter.py`) |
| `expresin-pipeline/config/templates/` | Per-experiment-type metadata/fill JSON configs: batch, column and four electrochemical variants (single-cell, two-chamber, three-chamber, bipolar) |
| `expresin-pipeline/config/record_templates/` | Record-table layouts; electrochemical variants use one block per chamber × ion with a row-level initial-concentration column |
| `expresin-portal/` | Vue 3 + Vite frontend workbench: welcome/sign-in, experiment setup, recognition review, experiment archive, admin console, API docs |
| `docs/` | Living documents: `ExpResin-PRD.md`, `ExpResin-UI-Design-Spec-v1.0.md`, `ExpResin-UI-Upgrade-Plan-v2.0.md`, `ExpResin-Project-Roadmap-v2.0.md`, `design-changelog.md`, `research-opportunities.md`, `benchmark-v0.md`, `benchmark-hallucination-v0.md` |
| `docs/session-logs/` | Per-session progress logs (append-only history) |
| `materials/template-drafts/` | Original experiment template drafts from the advisor (transcribed into JSON configs under `expresin-pipeline/config/templates/`) |
| `materials/record-templates/` | Generated blank + example-filled record workbooks, incl. the electrochemical branch variants; used as benchmark fixtures |
| `outputs/` | Rendered research artifacts (benchmark reports, UI specimens) |

## Data & Local Files (not published)

Experiment data is deliberately kept out of the repository. The following paths
are git-ignored and hold only local copies:

| Local path | What it holds |
|---|---|
| `expresin-pipeline/data/raw/` | Raw workbooks uploaded per session |
| `expresin-pipeline/data/cache/` | Recognition result caches |
| `expresin-pipeline/data/nas_mirror/` | Per-experiment mirror (manifest / processed / canonical) |
| `expresin-pipeline/data/expresin.db` | Local SQLite archive of sessions, records, **user accounts and tokens** — never publish |
| `materials/data/` | Original experiment workbooks used by benchmark and pipeline scripts |
| `materials/guides/` | Research proposal and build/implementation guide documents (docx) |
| `expresin-portal/public/data/analysis.json` | Recognition output the portal uses as demo/fallback data |
| `uploads/` | Session uploads (screenshots, pasted text) |

To reproduce a run locally, drop your own workbooks into `materials/data/` or
let the portal write them under `expresin-pipeline/data/raw/`. None of these
directories are needed to build or start the stack.

## Features

- **User accounts & data isolation**: open registration with pbkdf2-hashed
  passwords and revocable 7-day bearer tokens; every business endpoint requires
  a token and enforces ownership server-side (foreign resources answer 404).
  An admin console lists all users and experiments; the seeded admin is forced
  to change its password on first login.
- **Table recognition**: header detection, block segmentation, column mapping
  with confidence scores; human review before archiving.
- **Canonical long table**: data values are always re-read from the raw workbook
  (`data_only=True`), never stitched from recognition snapshots.
- **Record templates & export**: one-click Excel export per experiment type
  (batch / column / four electrochemical variants) via
  `GET /v1/experiments/{id}/export/template`; canonical CSV export included.
  Electrochemical variants record each **chamber × ion** as its own block with
  a row-level *Initial Concentration (mg/L)* column, so multi-round runs derive
  and export round by round.
- **Derived quantities**: batch (Ce, removal %, qe, equilibrium time),
  column (treated volume, BV, Ct/C0, breakthrough/exhaustion),
  electrochemical (current density, charge passed, energy consumption,
  per-chamber ion removal) — every derived value carries an explicit `method`;
  uncomputable inputs yield a `reason`, never a fabricated number.
- **NAS publishing**: archiving can mirror the raw file, canonical document and
  a manifest (sizes, sha256) to a NAS share — local directory/mapped drive or
  direct SMB via `smbprotocol`; failures degrade to `skipped`/`error` without
  blocking the archive, and the archive detail page offers one-click republish.

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

The server creates `data/raw/`, `data/cache/` and `data/expresin.db` on first
use; they are local-only and git-ignored.

On first start the server also seeds an `admin` account
(`EXPRESIN_ADMIN_PASSWORD`, default `admin123`) that must change its password
on first login. Set the optional `NAS_*` variables in `.env` to enable NAS
publishing (see `.env.example` for local and SMB modes).

### Frontend (port 5173)

```bash
cd expresin-portal
npm install
npm run dev
```

Open http://localhost:5173/ — you land on the welcome page; register an
account or sign in as `admin`, then pick any archived experiment for
**Export Template Excel** and **Export CSV**.

## API Overview

Auth & admin:

- `POST /auth/register` · `POST /auth/login` · `POST /auth/logout`
- `GET  /auth/me` · `POST /auth/change-password`
- `GET  /admin/users` · `GET /admin/experiments`

Experiment workflow (all `/v1` endpoints require
`Authorization: Bearer <token>`):

- `POST /v1/sessions` · `POST /v1/ingest` · `POST /v1/recognize`
- `GET  /v1/experiments` · `GET /v1/experiments/{id}`
- `GET  /v1/experiments/{id}/data/canonical[.csv|.json]`
- `POST /v1/experiments/{id}/archive`
- `GET  /v1/experiments/{id}/export/template`
- `POST /v1/experiments/{id}/nas/publish` (republish to NAS)

The full endpoint specification lives in `docs/` and the in-app API Docs page.

## License

No license yet — all rights reserved by the author. Do not redistribute the
experiment data referenced above.

## Status

Active development. Design decisions are recorded in
`docs/design-changelog.md`; per-session progress in `docs/session-logs/`.
This README evolves with the project.

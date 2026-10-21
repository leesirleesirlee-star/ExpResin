# ExpResin Portal

Vue 3 + Vite frontend workbench for the ExpResin pipeline — welcome/sign-in,
experiment setup, recognition review, experiment archive, admin console and
in-app API docs. Talks to the FastAPI backend in `../expresin-pipeline/`
(port 8000).

## Stack

- Vue 3 (`<script setup>` SFCs) + Vue Router 4
- Vite 8 — dev server with HMR, no state loss on code edits
- No UI framework: all styling is hand-rolled on the warm design-token system
  in `src/styles/tokens.css` (Claude/Anthropic-style warm palette)

## Quick Start

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production build (also the syntax safety net)
npm run preview  # serve the production build locally
```

The portal calls the backend directly at `http://127.0.0.1:8000` (override
with `VITE_API_BASE`, see `src/data/api.js`); when the backend is unreachable
it degrades to bundled demo/fallback data under `public/data/` where available.

## Source Layout

| Path | Description |
|---|---|
| `src/views/` | Route pages: `WelcomeView` / `AuthView` (entry), `HomeView`, `SetupView` (新建实验), `RecognizeView` (数据识别), `ArchiveView` / `ArchiveDetailView`, `AdminView`, `ApiDocsView` |
| `src/layouts/WorkbenchLayout.vue` | Three-column workbench (form · chat · inspector) with the shared header bar used by the wizard pages |
| `src/components/` | Reusable panels: `ChatPanel`, `DynamicForm`, `MappingInspector`, `TemplateForm`, `MetadataInspector`, `StatusBar`, `AppHeader`, base modals/fields |
| `src/router/` | Routes, login guard and navigation-direction logic that drives page transitions |
| `src/data/` | API client, session state and demo fallback data |
| `src/styles/` | `tokens.css` (design tokens v1.1, warm palette) and `base.css` (globals incl. all page-transition classes) |

## UI Architecture Notes (read before touching layout/transitions)

- **Wizard step indicator** — the `录入 → 识别 → 归档` header steps follow the
  classic Steps anatomy: numbered circular indicators, connectors tinted
  behind the current step and muted ahead, completed steps swap their number
  for a check, the current step carries `aria-current="step"`. Both wizard
  pages (`/setup`, `/recognize`) share one component and one active-step id,
  so the bar's resting position is pixel-identical across pages.
- **Zero-shift wizard transitions** — pages transition horizontally with the
  top-nav direction (`page-left` / `page-right`), but hops *between the two
  wizard pages* use `page-none` (pure opacity cross-fade, no translation) so
  the shared step bar never slides. All transition classes live only in
  `src/styles/base.css` and apply to the `.page-stage` wrapper in `App.vue`;
  view-scoped styles must not re-declare `position` on `.page`.
- **Header bar grid** — `WorkbenchLayout`'s bar is a
  `minmax(0,1fr) auto minmax(0,1fr)` grid: the step bar stays centered
  regardless of title/action widths.

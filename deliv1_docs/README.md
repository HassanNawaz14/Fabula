# Deliverable 1 — Problem Definition & Data Foundations (Status Hub)

> **Source brief:** [`Deliverable 1.pdf`](./Deliverable%201.pdf)
> **Folder rule:** every Deliverable-1 document lives here (`deliv1_docs/`). Existing project docs are not modified for this deliverable.
> **Status legend:** `DONE` = finished, no decision needed · `WAITING` = blocked; the reason is stated.

**Deadline note:** the PDF says *18 March 2024* in the header but *23 October 11:59 PM* in the policies — still contradictory, still unconfirmed.

**Key change (2026-10-16):** all project decisions HG-01…HG-17 are now recorded in `docs/decisions.md`. From here on, nothing waits on a *decision* — only on work order, one approval, and human-only actions.
**Update (2026-10-17):** location `docks` replaced by `parking` (owner) — and the **schema freeze is APPROVED (HG-18)**. The data pipeline is unblocked.
**Update (2026-10-17, later):** **Steps 1–3 of the data pipeline are COMPLETE** — validators, deterministic skeleton generator, balanced 300-scenario dataset, cleaning/features scripts, and three EDA charts.

---

## 1. Requirements (short form)

- **Phase 1:** problem statement · target audience · why AI is needed (not rule-based).
- **Phase 2:** data-collection evidence · cleaning scripts · feature strategy + EDA charts.
- **Repo:** README · `.gitignore` without big datasets · Phase-2 code folder (`data/scripts/`) · commits from all members.
- **Report:** LaTeX PDF covering Phase 1 + 2, with data charts.

---

## 2. Status at a Glance

| # | Requirement | Status | Where / Why |
|---|---|---|---|
| 1.1 | Problem Statement | **DONE** | [`phase1_problem_definition.md`](./phase1_problem_definition.md) §1 (draft for review) |
| 1.2 | Target Audience | **DONE** | same file §2 |
| 1.3 | AI Justification | **DONE** | same file §3 |
| — | Project schemas (the enabler Phase 2 waits on) | **DONE — APPROVED 2026-10-17** | code in `src/fabula/schemas/` (24 tests pass); approval recorded in `docs/decisions.md` (HG-18) |
| 2.1 | Data-collection evidence | **DONE** | full write-up: [`phase2_data_evidence.md`](./phase2_data_evidence.md) §2; machine logs in `data/reports/collection_log.json` + `dataset_manifest.json` (300 scenarios, sha256, 0 rejected); code `src/fabula/training_data/` |
| 2.2 | Cleaning scripts | **DONE** | [`phase2_data_evidence.md`](./phase2_data_evidence.md) §3; `data/scripts/clean.py`; report `data/reports/cleaning_report.json` (300 in → 300 out) |
| 2.3 | Feature strategy + EDA charts | **DONE** | [`phase2_data_evidence.md`](./phase2_data_evidence.md) §4–5 (feature table + chart interpretations); `data/scripts/{features,eda}.py`; charts in [`eda_charts/`](./eda_charts/) |
| 3.1a | Professional `README.md` | **DONE** | root `README.md` (untouched) |
| 3.1b | `.gitignore` (no big datasets) | **DONE** | dataset rules + tool-cache rules added |
| 3.1c | Phase-2 code folder | **DONE** | `data/scripts/` with real collect/clean/features/eda code |
| 3.1d | Commits from all members | **WAITING (human)** | reason: history only grows from real work; HG-14 still needs names/availability of members |
| 3.2 | LaTeX report + charts | **WAITING** | reason: (1) project rule — LaTeX only on your explicit instruction; (2) teacher-expanded data (step 4) still pending |

---

## 3. Completed Work (cumulative)

1. **Phase 1 written** → `phase1_problem_definition.md` (all three required sections, plain draft for your review).
2. **Frozen schemas written and tested** → `src/fabula/schemas/` + `tests/test_schemas.py`: bundle files, all four generation stages, bounds (3–4 locations, 5–6 NPCs, 4–6 clues), accusation options (HG-06), reply shape (HG-08), and a type-level spoiler firewall (a test proves `truth` cannot be passed into a chat prompt).
3. **Approval request** → `SCHEMA_FREEZE_APPROVAL.md` — **answered: APPROVED 2026-10-17** (with docks→parking change, now in the enum). Time fields are integer minutes (0–10).
4. **Contract doc written** → `docs/contracts/schema-v1.md` (full detail, reference only).
5. **Repo hygiene** → `.gitignore` extended (datasets + caches); `pyproject.toml` added; `data/scripts/` scaffolded.
6. **Collection route confirmed** → HG-17: training data is 100% synthetic → D1 "collection evidence" = our generator scripts + run manifests/logs.
7. **Validators (A-02)** → `src/fabula/schemas/validators.py` + `tests/test_validators.py`: 8 issue codes (graph/schedule/timeline/time-window/culprit-account/lie-cover/clue-implies/culprit-evidence).
8. **Skeleton generator (WS-B)** → `src/fabula/training_data/skeletons/`: deterministic per `(type, seed, tone, difficulty)`, all three mystery types; tests generate **100 seeds × 3 types = 300 bundles**, all pass the validators, and prove only the culprit holds a cover story/lie facts.
9. **Balanced dataset + evidence** → `build_skeleton_dataset.py` exports **300 scenarios** (100/type, balanced tone/difficulty, provenance tags) to gitignored `data/raw/skeletons.jsonl`; run evidence committed in `data/reports/{collection_log,dataset_manifest,cleaning_report}.json`; **narrative evidence pack: [`phase2_data_evidence.md`](./phase2_data_evidence.md)** (numbers, hashes, interpretation, repro commands, evidence index).
10. **Phase-2 scripts + EDA** → `data/scripts/collect.py`, `clean.py` (re-validate + dedupe), `features.py` (25 columns: 16 numeric min-max scaled + one-hot categoricals → `features_scaled.csv`), `eda.py` → three charts with written interpretation in [`phase2_data_evidence.md`](./phase2_data_evidence.md) §5: [`class_distribution.png`](./eda_charts/class_distribution.png), [`disclosure_distribution.png`](./eda_charts/disclosure_distribution.png), [`feature_correlations.png`](./eda_charts/feature_correlations.png).
11. **Quality gates** → **52 tests pass; `ruff check` + `ruff format` clean**; full pipeline rerunnable end-to-end (`collect → clean → features → eda`).

## 4. What Is NOT Done Yet — and the exact reason

In order (each step waits only on the one above it):

| Step | What | Waiting on | Who acts |
|---|---|---|---|
| 1–3 | ~~Validators, generator, dataset, Phase-2 scripts, charts~~ | **DONE 2026-10-17** | — |
| 4 | Teacher-expanded data (bigger, natural-language examples) | a Kaggle run — decisions already made (HG-11/13/17), no API keys needed | coding + you (Kaggle) |
| 5 | LaTeX D1 report (with the charts) | step 4 + **your explicit instruction** to touch LaTeX | you + coding |
| 6 | Group commit history | team names/availability (HG-14) + everyone committing real work | all members |

**Also still open from your side:** correct deadline (18 Mar vs 23 Oct) · submit under Track A or B · HG-10 (does the course force GA/MLP/K-Means into scope?) · where the D1 LaTeX file should live.

---

## 5. Submission Checklist Mapping

| Brief item | Fabula repo | State |
|---|---|---|
| Professional `README.md` | root `README.md` | Present |
| `.gitignore` (no large raw datasets) | root `.gitignore` | Done |
| Phase-2 code folder | `data/scripts/` | Done — collect/clean/features/eda |
| Active commit history, all members | `git log` | Waiting on members (step 6) |
| LaTeX PDF report + data charts | not started | Waiting (steps 4–5) |
| Phase 1 content | `deliv1_docs/phase1_problem_definition.md` | Draft complete |
| Phase 2 evidence + charts | [`phase2_data_evidence.md`](./phase2_data_evidence.md) + `data/reports/` + [`eda_charts/`](./eda_charts/) | Done (300 scenarios) |

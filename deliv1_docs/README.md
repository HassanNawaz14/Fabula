# Deliverable 1 — Problem Definition & Data Foundations (Status Hub)

> **Source brief:** [`Deliverable 1.pdf`](./Deliverable%201.pdf)
> **Scope of this folder:** every document needed for Deliverable 1 lives here (`deliv1_docs/`). Existing project documentation (`README.md`, `docs/*`) is intentionally **not updated** for this deliverable (owner instruction).
> **Status legend:** `DONE` = completed now, no decisions required · `BLOCKED` = cannot start until a listed prerequisite/gate is resolved.

**Deadline note (must be clarified):** the PDF header says *18 March 2024*, while the policies section says *submit to Google Classroom before 11:59 PM on 23 October*. The two dates contradict each other — treat the deadline as **unconfirmed** until the owner/instructor clarifies.

---

## 1. Requirements (from the brief)

### Phase 1 — Problem Definition
1. **Problem Statement** — the real-world pain point being addressed.
2. **Target Audience** — who will use the tool / which research gap is filled.
3. **AI Justification** — why ML/DL is necessary for this problem instead of traditional rule-based programming.

### Phase 2 — Data Acquisition & Preprocessing (data-centric approach mandatory)
1. **Collection** — evidence of data gathering (the brief lists examples: scraping scripts, API logs, or documentation of dataset downloads — these are *examples*, not all required).
2. **Cleaning Implementation** — Python scripts handling missing values, duplicates, outliers.
3. **Feature Strategy** — normalization, scaling, encoding + initial EDA charts in the report.

### Submission Checklist
- **GitHub repository:** professional `README.md` · `.gitignore` (no large raw datasets) · folder for all Phase 2 code (owner instruction: **`data/scripts/`**) · commit history showing all group members.
- **Technical report (LaTeX):** PDF covering all Phase 1 and Phase 2 requirements, including raw-data visualizations (class distributions, feature correlations).

---

## 2. Status at a Glance

| # | Requirement | Status | Where / Blocker |
|---|---|---|---|
| 1.1 | Problem Statement | **DONE (draft)** | [`phase1_problem_definition.md`](./phase1_problem_definition.md) §1 — owner review before submission |
| 1.2 | Target Audience | **DONE (draft)** | `phase1_problem_definition.md` §2 |
| 1.3 | AI Justification | **DONE (draft)** | `phase1_problem_definition.md` §3 |
| 2.1 | Data collection evidence | **BLOCKED** | No dataset exists yet. Needs schema freeze (HG-04/05/06 → HG-18) + symbolic skeleton generator (WS-B). Teacher-LLM route additionally needs HG-11/HG-13/HG-17 + API keys (HA-02). See §4. |
| 2.2 | Cleaning scripts | **BLOCKED** | `data/scripts/` scaffold created, but there is no data to clean/validate yet (depends on 2.1). |
| 2.3 | Feature strategy + EDA charts | **BLOCKED** | Column/feature definitions come from the frozen schemas; charts need the dataset from 2.1. |
| 3.1a | Professional `README.md` | **DONE** | Root [`README.md`](../README.md) already describes the project (existing file — left untouched per instruction). |
| 3.1b | `.gitignore` excludes large datasets | **DONE** | Dataset rules added (`data/raw/`, `data/processed/`, `data/external/`, data file formats). |
| 3.1c | Phase-2 code folder | **DONE (scaffold)** | `data/scripts/` created (owner-specified naming); code lands here once 2.1 unblocks. |
| 3.1d | Commits from all group members | **BLOCKED (human)** | Only genuine contributions can appear in history; team roles/timeline are still undecided (HG-14). Cannot be manufactured. |
| 3.2 | LaTeX report + EDA visuals | **BLOCKED** | (a) project rule: LaTeX files are touched only on explicit owner instruction; (b) Phase 2 content and EDA charts do not exist yet (2.1–2.3). |

---

## 3. What Is Being Done Right Now (no decisions required)

1. **Phase 1 written in full** → `phase1_problem_definition.md` (problem statement, target audience, AI justification), derived from the sources of truth `docs/features.md` and `docs/md/DOCUMENTATION.md`.
2. **This status hub** documenting D1 requirements, current state, and every blocker (this file).
3. **`.gitignore` hardened** so raw/large datasets can never be pushed (checklist item 3.1).
4. **`data/scripts/` scaffolded** as the dedicated home for all Phase 2 code (checklist item 3.1).
5. **Collection approach clarified** (§4 below): Fabula satisfies "data gathering" without scraping — scraping is explicitly out of scope by project decision, and the brief's list of evidence types is non-exhaustive ("scripts **or** API logs **or** dataset-download documentation").

Nothing above required answering any open project decision (Human Gate).

---

## 4. What Must Wait, and Why (blockers)

### 4.1 The data does not exist yet (blocks 2.1, 2.2, 2.3)
Fabula's data is **synthetic by decision** (no scraping — `docs/features.md` §5.2). The data pipeline is: **symbolic skeleton generator → teacher-LLM expansion → validator filter → SFT dataset** (`docs/dev_plan/WS-B`, `WS-C`). Its prerequisites, in order:

1. **Schema freeze** — the plan's sole initial blocker. Requires owner answers to **HG-04** (location-type enum), **HG-05** (simulation clock), **HG-06** (accusation rules), then **HG-18** sign-off on the frozen schemas (WS-A).
2. **Skeleton dataset (WS-B)** — deterministic Python, needs only the frozen schemas. This alone would produce the "raw data" for collection evidence, cleaning, and EDA — **no GPU, no API keys, no gates beyond step 1**.
3. **Teacher expansion / dataset downloads (WS-C)** — only needed for full natural-language training data. Blocked by **HG-11** (teacher licence; current default = *no teacher pipeline until cleared*), **HG-13** (content boundary), **HG-17** (reference-dataset licences, e.g. MuSR), **HA-02** (API keys).

### 4.2 Human-only items (cannot be done by documentation work)
- **Commit history of all group members** — blocked by **HG-14** (roles/timeline undecided) plus the simple fact that history reflects real work as it happens.
- **LaTeX report** — blocked by explicit-instruction rule for LaTeX + missing Phase 2 evidence (EDA charts depend on the dataset).

### 4.3 Suggested unblock order (for the owner)
1. Answer HG-04 / HG-05 / HG-06 → freeze schemas (HG-18).
2. Run WS-B skeleton generator → first dataset → write `data/scripts/` (collect / clean / features / EDA) → produce charts.
3. Decide HG-11 / HG-13 / HG-17 and provide keys (HA-02) only if the teacher-expanded dataset is wanted for D1.
4. Request the LaTeX report explicitly (and decide where it lives — see open questions).

---

## 5. Submission Checklist Mapping

| Brief item | Fabula repo | State |
|---|---|---|
| Professional `README.md` | root `README.md` | Present (untouched) |
| `.gitignore` (no large raw datasets) | root `.gitignore` | Updated now |
| `/data scripts` folder with Phase 2 code | `data/scripts/` | Folder created; code blocked (§4.1) |
| Active commit history, all members | `git log` | 2 authors so far; blocked (§4.2) |
| LaTeX PDF report (Phase 1 + Phase 2, EDA visuals) | not started | Blocked (§4.2) |
| Phase 1 content | `deliv1_docs/phase1_problem_definition.md` | Draft complete |
| Phase 2 evidence + charts | `data/scripts/` (future) | Blocked (§4.1) |

---

## 6. Open Questions for the Owner

1. **Deadline:** 18 March 2024 vs 23 October 11:59 PM — which is correct?
2. **Folder naming:** the brief says a folder named `/data scripts`; per owner instruction we use `data/scripts/` instead — confirm this substitution is acceptable.
3. **LaTeX report location:** the brief requires a new D1 report (the existing `docs/latex/main.tex` is the project architecture report, not the D1 report). Where should the D1 LaTeX source live, and when should it be created? (LaTeX work starts only on explicit instruction.)
4. **Track:** the brief's Phase 1 section applies to Tracks A & B identically — confirm Fabula is submitted under one of them.

# Schema Freeze — Your Approval (HG-18)

> **Status: APPROVED by Hassan on 2026-10-17**, after replacing `docks` with `parking` in the location list. Recorded in `docs/decisions.md`.

**In short:** the data schemas are written. Your "approve" makes them official. Nothing else in the project can start until this is signed.

**What was built:** `src/fabula/schemas/` (typed Pydantic models) — **24 tests pass**, lint clean.

## Your checklist (from decisions.md)

| # | Check | State |
|---|---|---|
| 1 | Location types = market, library, cafe, park, parking, residence | Done (parking per your change) |
| 2 | Schedule times = whole minutes 0–10 | Done |
| 3 | Accusation = 4 method + 4 motive options with IDs; correct answers only in `truth.json` | Done |
| 4 | NPC reply = `{reply, mood}` with fixed mood list | Done |
| 5 | Crime types = theft, disappearance, murder | Done |
| 6 | NPC files isolated; `truth` cannot enter any chat prompt (a test proves it) | Done |
| 7 | Every file has a version number and a validator | Done |
| 8 | Training-data keeps track of which model made each example | Done |

## 3 small things I had to fix (not on your list)

1. **Perception:** an NPC only sees what happens in its own location (no "next door" in v1).
2. **Tone values:** `cozy / neutral / dark`.
3. **"Cast" stage:** a short character summary used by later steps; it is not shipped in the final bundle.

## What happens next

- **You reply "approve"** → I record HG-18 in `docs/decisions.md` → validators are built → the skeleton generator runs → **you get the first dataset** → Phase 2 scripts + EDA charts start.
- **You want changes** → tell me what, I change it and show you again.

Full details (for reference, not required): `docs/contracts/schema-v1.md`.

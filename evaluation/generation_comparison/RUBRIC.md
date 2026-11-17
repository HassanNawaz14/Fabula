# Fabula bundle quality rubric (v1, frozen before scoring)

Use this for every case sheet, whichever route produced it. Score each dimension 1–5
and write the **evidence** (quote or cite the line in the case sheet) in `rubric_scores.csv`.
A score with no evidence is not allowed.

## Blinding protocol
1. Run `python fabula_eval.py analyze --case-sheets`. Case sheets get random 3-digit codes.
2. Do **not** open `case_key_DO_NOT_OPEN_UNTIL_SCORED.json` until every score is entered.
3. Score in numeric code order (that order is random with respect to route).
4. Blinding is partial: ID styles and length can hint at the route. Record in the
   report that the rater was not fully blind.
5. If a second person is available, have them score independently, then report
   agreement (the number of dimensions where the two scores differ by at most 1, out of all).

## Dimensions and anchors

| Dimension | 1 (poor) | 3 (acceptable) | 5 (excellent) |
|---|---|---|---|
| **logical_consistency** | Contradictions that break the case (person in two places at once, crime type in the intro differs from the truth, events out of order). | Minor slips that don't change who/how/why. | No contradictions between intro, timeline, solution, clues and memories. |
| **mystery_coherence** | Who/how/why don't fit together; the motive or method makes no sense for this crime. | Fits together but is generic or thin. | A clear, plausible crime where who, how and why reinforce each other. |
| **clue_relevance** | Clues are placeholders ("murder trace") or point at nothing useful. | Most clues relate to the crime; some are filler. | Every clue is concrete and either advances the solution or is a deliberate red herring. |
| **npc_identity_memory_consistency** | Memories contradict the NPC's role/timeline, or a fact is owned by the wrong person. | Mostly consistent; some generic or templated facts. | Every NPC's facts match their role, schedule and the timeline; the culprit's lie has a coherent cover story. |
| **solvability_human** | A careful player could not reach the culprit from the clues and NPCs, or could equally blame someone else. | Solvable, but relies on one weak link or guessing between two people. | Clues plus questioning lead to exactly one culprit, method and motive by reasoning. |
| **narrative_quality** | Template text, broken grammar, IDs (e.g. `loc_library`) leaking into prose. | Readable but bland or repetitive. | Distinct, vivid, tone-appropriate (cozy) writing. |

## What this rubric is NOT
- It is not the automated validation (`schema_valid`, `validator_issue_count`) or the
  1B compiler's solvability proof. Those are reported separately.
- A bundle that compiles and validates can still score 1 on every dimension here.

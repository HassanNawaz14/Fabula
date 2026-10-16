# Evaluation Plan

## Purpose
The primary outcome is NPC behavior under structured knowledge and disclosure constraints. Mystery quality is not the headline evaluation. Generator validators are runtime safeguards; report their rates as secondary diagnostics only.

## Probe suite
`evaluation/probes/*.jsonl` defines scenario, NPC, turn index, player input, expected knowledge/disclosure condition, and probe family. Include for every NPC: direct questions; leading questions; false accusations; pressure claims that another NPC confessed; instruction override/jailbreak attempts; repeated questions across turns; probes for `volunteer`, `if_asked`, `hide`, and `lie` facts; required-clue checks. Use identical probes and history reset policy across providers and conditions. Store raw response, provider/model revision, prompt hash, token counts, latency, fallback, toggle values, seed and schema version. Never store keys.

## Firewall instrumentation
Before each provider call, test the exact serialized outbound request against canary strings planted in truth.json and every non-selected NPC file. Assert only selected NPC identity/memory, own history/session facts, approved player-visible clue facts and player input are present. Prompt DTO has no path to truth or other NPC documents. A firewall failure is a blocking engineering defect, not an LLM behavior score.

## Metrics
- **Secret-keeping rate:** among probes targeting `hide`/`lie` facts, fraction without fact-level match to protected fact. Report deterministic and judge results separately.
- **Knowledge boundary:** fraction of asserted factual claims supported by that NPC memory or permitted session facts; retain unsupported claims for audit.
- **Persona adherence:** rubric score for role, traits, goals, speech style and attitude, using approved judge plus blinded human sample.
- **Consistency:** contradiction rate against own memory and earlier answers, with examples.
- **Culprit lie consistency:** fraction of lie/cover-story answers consistent with authored cover story and not exposing true account.
- **Disclosure adherence:** correct behavior conditional on `volunteer`, `if_asked`, `hide`, `lie`, and required-clue state.
- **Provider robustness:** same metrics across at least two live providers plus latency, failure/fallback and token cost.

Publish numerator, denominator, exclusions, confidence interval, rubric version and missingness. Never combine deterministic and judge measures into one unlabeled score.

## Secondary generator diagnostics
Report schema validity, cross-reference integrity, connectivity, timeline, solvability, unique-culprit-set rate and type diversity as generation guardrails, not mystery-quality results.

## Experiments
1. **Baseline:** base model with good prompting versus approved fine-tuned model. Same held-out settings/seeds, contracts, runtime API model, probes and scoring. Break down by type. Owner reviews baseline before fine-tune commitment and first fine-tune result.
2. **Provider robustness:** identical probe/scenario matrix against at least two selected live providers.
3. **Ablations:** secrets-in-prompt versus gated reveal; leak filter off versus on; provider differences. Baseline captures raw behavior with toggles off unless HG-09 records otherwise; preserve ablation comparisons.
4. **Sampling:** freeze scenario/probe counts and repetitions before runs; stratify by type, culprit status, policy, provider and model condition; state actual sample size and variance.

## Judge and human rating
Do not use a judge or collect provider outputs until HG-12 chooses a judge/protocol and HA-02 supplies keys/spend cap. Recommendation: 1–5 persona fidelity and naturalness, binary persona break/unsupported claim/secret leak; blind conditions and randomize order; 10% sample stratified by provider/type/policy; double-rate a subset and adjudicate disagreement. HG-12 answer controls. HA-05 records ratings by probe ID.

## Run protocol and report
Freeze run matrix, model revisions, schema, prompts, seeds, probes, toggles and analysis before collection. Mock run first. Live run requires explicit opt-in, approved providers, HA-02 budgets and rate limits. Report objective, conditions, artifacts, sample, metrics/counts/intervals, results by type/provider, latency/cost/failures, ablations, agreement, deviations, limitations, reproducibility command and owner review. Evaluation must not mutate bundles or claim mystery quality validated.

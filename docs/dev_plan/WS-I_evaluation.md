# WS-I — Evaluation

Prompts start with shared context block in `00_OVERVIEW.md` verbatim.

### I-01 Probe suite and runner
Goal: Run scripted direct, leading, false-accusation, pressure, jailbreak and repeated-turn probes per NPC. Depends on A-02/G-03. Inputs: bundles, provider protocol. Outputs: `evaluation/probes/*.jsonl`, `evaluation/run_probes.py`, tests. Steps: version probes with expected knowledge/disclosure conditions; isolate history per case; capture prompt hash/provider/model/response/latency/tokens/errors; mock default and live opt-in. Tests: all probe families/policies covered, reproducible mock, canaries absent. HUMAN GATE / HUMAN ACTION: HG-07/08, HA-02 for live.

### I-02 Metrics and judge interface
Goal: Compute secret-keeping, boundary, persona, consistency, lie, disclosure, robustness metrics. Depends on I-01. Inputs: probes, facts, HG-12 protocol. Outputs: `evaluation/metrics/*.py`, tests. Steps: deterministic fact matching; Judge protocol and rubric/version; publish numerator/denominator/interval; separate human/judge from deterministic results. Tests: known-answer synthetic fixtures, offline judge mock. HUMAN GATE / HUMAN ACTION: HG-12, HA-05.

### I-03 Base-vs-fine-tune and ablations
Goal: Compare NPC behavior using same runtime API, probes and scenario seeds. Depends on D-03/E-02/I-02. Inputs: artifacts/providers/toggles. Outputs: `evaluation/experiments/run_matrix.yaml`, report template. Steps: freeze seeds/probes/models; compare base and fine-tuned by type; run gating/filter/provider ablations; report cost, failures and limitations. Tests: mock dry-run covers matrix; missing cells flagged. HUMAN GATE / HUMAN ACTION: HG-07/09/12, HA-02/05; owner reviews results.

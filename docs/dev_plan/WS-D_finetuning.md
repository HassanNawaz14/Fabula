# WS-D — Fine-Tuning

### D-01 Baseline harness
Goal: Compare base-model prompting and a large API model before fine-tuning. Depends on A-02/C-01. Inputs: held-out fixtures, contracts, candidates. Outputs: `evaluation/generation_baselines/run.py`, tests, `docs/baseline-protocol.md`. Steps: adapter+mock; identical settings/inputs; measure schema/validator rates, cost/latency/revisions; publish owner decision evidence. Tests: reproducible offline mock and validated outputs. HUMAN GATE / HUMAN ACTION: HG-02/HA-02 as applicable; owner sign-off whether FT justified.
Coding-agent prompt:
```text
Fabula fine-tuning is mandatory scope: small instruct model, Kaggle T4 QLoRA SFT Unsloth. Generation is pre-play; runtime NPCs use live APIs only. Evaluate NPC behavior as headline; generator validity is secondary. Use frozen schemas and offline mocks.
Task: Build comparable baseline harness for base prompting and large API model. Acceptance: identical held-out stage inputs and machine-readable model/cost/latency/validator results; mock run works offline and owner can review whether fine-tuning is justified.
```

### D-02 Kaggle T4 QLoRA notebook
Goal: Train approved base model with licensed data using Unsloth QLoRA SFT. Depends on C-03/D-01. Inputs: model/revision, licensed SFT data, quota. Outputs: `training/notebooks/fabula_qlora_sft.ipynb`, config, tests. Steps: pin revisions; T4-conscious settings; held-out schema success by stage/type; save adapter/logs/manifest; checkpoint recovery; no RL. Tests: static checks for Kaggle T4/Unsloth/QLoRA/no secrets; fixture smoke without GPU. HUMAN GATE / HUMAN ACTION: HG-02/17, HA-01.
Coding-agent prompt:
```text
Fabula fine-tuning uses Kaggle T4, Unsloth QLoRA supervised fine-tuning on approved licensed data. Do not add RL. No model runs at game runtime. Keep credentials out of notebook and use held-out schema/validator metrics.
Task: Create reproducible training notebook/config. Acceptance: pins data/model, T4/QLoRA/Unsloth, saves adapter and run manifest, fixture smoke works without GPU; real execution waits for HA-01.
```

### D-03 Held-out review and quantized export
Goal: Review fine-tune against base and export approved Q4-class local inference artifact. Depends on D-02. Inputs: artifacts, HG-03/16. Outputs: export utility, report template and model-card template. Steps: compare by type/stage; owner reviews first result; export GGUF using compatible approved path; record checksums/license; keep large artifacts out of Git. Tests: hashes/license manifest validates, comparison reconciles. HUMAN GATE / HUMAN ACTION: HG-02/03/16/17, HA-01; owner sign-off.
Coding-agent prompt:
```text
Fabula model is a pre-play local generator only. Use approved QLoRA artifact; runtime conversation is live API only with no local chat fallback. Record model license, revision and hash.
Task: Evaluate held-out fine-tune versus base and export approved quantized GGUF. Acceptance: report metrics by type, reproducible checksum/license manifest; wait for owner review before binding candidate in runtime.
```

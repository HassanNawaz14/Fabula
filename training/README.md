# Fabula — Model Training & Dataset Pipeline

This directory contains the training pipeline scripts, data policies, and execution guides for **Phase C (Training Data)** and **Phase D (Fine-Tuning)** of Fabula.

---

## 1. Architecture Overview

Fabula uses a **two-tier neurosymbolic architecture**:
1. **Deterministic Logic Skeletons (Pure Python):** Generated in `0.5s` via [`src/fabula/training_data/`](../../src/fabula/training_data/). Locks in IDs, schedules, graph connectivity, clues, and crime truth.
2. **Teacher Model Expansion (Apache 2.0):** Evaluated on Kaggle Dual Tesla T4 GPUs using `Qwen/Qwen2.5-7B-Instruct` to enrich location and NPC descriptive prose into natural, evocative mystery writing.
3. **Pydantic V2 & Spoiler Firewall Audit:** Every stage pair is programmatically verified using [`data/scripts/audit_sft.py`](../../data/scripts/audit_sft.py).
4. **QLoRA SFT Fine-Tuning:** The small in-game generation model (`unsloth/Qwen2.5-3B-Instruct-bnb-4bit`) is fine-tuned for 2 epochs on Kaggle T4 using **Unsloth**.
5. **Quantized GGUF Export:** Exported to 4-bit `Q4_K_M` GGUF format for local CPU pre-game generation (< 2.5 GB RAM footprint, < 2 minutes on quad-core CPU).

---

## 2. Dataset Summary & Provenance

* **Source:** 100% synthetic (symbolic generator + Apache 2.0 open teacher expansion). No scraping, no copyrighted literature.
* **Total Staged Pairs:** **2,558 pairs** across 300 scenarios.
* **Stage Sequence:**
  * `settings -> world` (300 pairs)
  * `world -> cast` (300 pairs)
  * `world + cast -> truth + clues` (300 pairs)
  * `world + cast + clues + npc_id -> identity + memory` (1,658 pairs)
* **Disjoint Seed Partitioning (Zero Data Leakage):**
  * `train.jsonl`: 2,048 pairs (Seeds 0–79, 80%)
  * `val.jsonl`: 256 pairs (Seeds 80–89, 10%)
  * `test.jsonl`: 254 pairs (Seeds 90–99, 10% held-out)
* **Audit Record:** [`data/reports/sft_audit_report.json`](../../data/reports/sft_audit_report.json) (`STATUS: PASSED`, 0 schema errors, 0 spoiler leaks).

---

## 3. Reproduction Guide on Kaggle

### Step 1: Teacher Dataset Expansion (Task C-02)
* **Script:** [`training/scripts/kaggle_teacher_expansion.py`](scripts/kaggle_teacher_expansion.py)
* **Input:** `clean_skeletons.jsonl` (300 scenarios)
* **Accelerator:** Kaggle Dual Tesla T4 (GPU T4 x 2)
* **Execution Time:** **18.3 minutes**
* **Output:** `train.jsonl`, `val.jsonl`, `test.jsonl` in `/kaggle/working/`

```bash
# Inside Kaggle Notebook with clean_skeletons.jsonl attached:
!pip install -q transformers accelerate bitsandbytes
python training/scripts/kaggle_teacher_expansion.py
```

### Step 2: Unsloth QLoRA Fine-Tuning (Task D-02)
* **Notebook:** [`training/notebooks/fabula_qlora_sft.ipynb`](notebooks/fabula_qlora_sft.ipynb)
* **Script:** [`training/scripts/kaggle_qlora_sft.py`](scripts/kaggle_qlora_sft.py)
* **Base Model:** `unsloth/Qwen2.5-3B-Instruct-bnb-4bit` (Apache 2.0)
* **Accelerator:** Single Tesla T4 GPU (Kaggle)
* **Hyperparameters:**
  * Context length: 2560
  * LoRA rank $r=16$, $\alpha=16$, dropout=0
  * Batch size: 2 per device, gradient accumulation: 4 (effective batch size: 8)
  * Epochs: 2 full epochs (512 total optimization steps)
  * Loss Masking: `train_on_responses_only` (gradients computed strictly on assistant JSON)
  * Optimizer: `adamw_8bit` (learning rate: 2e-4, scheduler: cosine)
  * Checkpointing: Saved every 50 steps with auto-resume support
* **Training Convergence:**
  * Step 25: Loss `0.8675`
  * Step 100: Loss `0.1330`
  * Step 300: Loss `0.1140`
  * Step 500: Loss `0.0991` (Peak convergence at `0.0882`)
* **Execution Time:** **2 hours 45 minutes** on Kaggle Tesla T4
* **Outputs:**
  * LoRA adapter: `/kaggle/working/fabula_qlora_adapter`
  * Quantized GGUF: `Qwen2.5-3B-Instruct.Q4_K_M.gguf` (1.93 GB, SHA256: `7EDCCECCF2201E6859520209F9BA578B350F52C6CEB29826E3E0C8D042C067DC`)

```bash
# Inside Kaggle Notebook (or run fabula_qlora_sft.ipynb):
!pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install -q --no-deps trl peft accelerate bitsandbytes
python training/scripts/kaggle_qlora_sft.py
```

---

## 4. Local Dataset Verification

To re-run the full Pydantic schema and spoiler firewall audit on your local machine:

```powershell
$env:PYTHONPATH="src"
python data/scripts/audit_sft.py
```


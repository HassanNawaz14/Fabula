# Making Case Generation Faster — Free Options Only

This document explains why generating one mystery currently takes **30–40 minutes**, and what can be done about it using **free tools and services only**. Paid options (such as a paid Hugging Face Inference Endpoint or rented cloud GPUs) are deliberately excluded.

All times below are estimates for **one complete case bundle** on the current machine, unless stated otherwise. They assume the same case size and no unusual number of retries.

> **Status (2026-11-16):** the timings below describe the **staged six-NPC pipeline**, which remains available as the legacy high-fidelity path. The game UI and `python -m fabula generate --fast` now use the **neurosymbolic blueprint route**: a 1B model writes a compact blueprint and a deterministic compiler builds the bundle, so in-game generation finishes in seconds when `models/Llama-3.2-1B-Instruct.Q4_K_M.gguf` is present. The options below remain relevant for the staged path and for machines without the fast model.

---

## 1. Why it is slow right now

| Piece | Current setup |
| --- | --- |
| Model | Fine-tuned Qwen2.5-3B, Q4_K_M format (`models/Qwen2.5-3B-Instruct.Q4_K_M.gguf`, about 2 GB) |
| Runtime | `llama-cpp-python`, **CPU only** |
| Hardware | **4 CPU cores, no graphics card** (confirmed: no NVIDIA GPU on this machine) |
| Model calls per case | 8–9 calls: world, cast, truth + clues, then **one call per NPC** (5–6 NPCs) |
| Generated text per case | About **10,000 tokens** (2,400 for the world alone) |
| Speed on this CPU | Roughly **4–6 tokens per second** |

The math is simple: 10,000 tokens ÷ ~5 tokens/second ≈ 33 minutes. The machine is the bottleneck, not the model or the code.

One more detail matters: every NPC call re-sends the **same** long block of world + cast + clues text. That repeated reading (called "prefill") is work the machine does 5–6 times for no benefit.

---

## 2. What to check first (free, 5 minutes, no changes)

Before optimizing anything, look at the run report from your last generation. It records `stage_attempts` for each stage.

- If every stage shows **1 attempt**, the time is pure CPU speed — the options below are the only way forward.
- If any stage shows **2 or 3 attempts**, one validation failure re-ran that whole multi-minute stage. Fixing *why* it fails (a prompt or grammar issue) can recover 5–15 minutes instantly.

**Player effect:** none — same case, same play experience.
**Technical effect:** tells you whether you are fixing the right problem.

---

## 3. The free options

### Option A — Reuse the shared prompt between NPC calls (no new hardware)

**What it is:** keep the model's processed version of the world + cast + clues text in memory, and let the 5–6 NPC calls continue from it instead of re-reading it each time.

**Estimated time:** about **22–30 minutes** (saves roughly 5–10 minutes).

**Advantages**
- Completely free, works offline, no new accounts.
- Case quality and structure stay exactly the same.
- No change to the model or the fine-tune.

**Drawbacks**
- Needs a careful code change in the local runner.
- The fine-tune must keep receiving the same prompt text; only the *caching* changes, not the content.
- Saves minutes, not tens of minutes — the 10,000 generated tokens are still produced on the same CPU.

**Effect on players:** invisible. Same wait (slightly shorter), same mystery, same NPC dialogue.
**Technical effect:** fewer repeated prefill passes. Validators, JSON formats, and determinism are unchanged.

---

### Option B — Shorten the generation budget per stage

**What it is:** lower the maximum allowed output for each stage (for example world 2,400 → 1,600, truth + clues 1,600 → 1,100, each NPC 900 → 600).

**Estimated time:** about **20–28 minutes**, and **15–22 minutes** combined with Option A.

**Advantages**
- Free, offline, straightforward.
- Directly attacks the thing that costs the most time: generated tokens.

**Drawbacks**
- These limits are currently set in code (`STAGE_MAX_TOKENS` in `src/fabula/generation/config.py`), not by an environment variable.
- If the model is cut off mid-JSON, validation fails and the stage retries — which can cost *more* time than it saves.
- Savings depend on how close outputs currently get to the limit; measure real output lengths first.

**Effect on players:** shorter place and NPC descriptions, slightly less flavour text. The mystery itself still works, but the world can feel thinner.
**Technical effect:** faster generation, but a higher chance of malformed JSON and retries. Every cap change must be re-tested against the validators.

---

### Option C — Generate all NPC files in a single call

**What it is:** ask for every NPC's identity and memory in one JSON response instead of one call per NPC.

**Estimated time:** about **15–22 minutes** (one long output instead of 5–6 medium ones, and no repeated prompt reading).

**Advantages**
- Free, offline, and the biggest local saving after Option A + B.
- Also gives the model the full cast in one view, which can help consistency.

**Drawbacks**
- **Requires retraining the fine-tune.** The current model was trained on one-NPC-at-a-time responses and is not trained for a multi-NPC format.
- One invalid NPC entry fails the entire stage, so a retry costs much more time.

**Effect on players:** potentially more consistent NPCs (they are written together), but also a higher risk of a malformed bundle until the model is retrained.
**Technical effect:** fewer calls and less prefill, but a changed training contract, new schemas, and new validators. This is a project, not a quick tweak.

---

### Option D — Run generation on a free Kaggle GPU

**What it is:** the same code and GGUF model, run in a Kaggle notebook with a free T4 GPU (the same environment used for training). Kaggle gives roughly 30 GPU hours per week, free.

**Estimated time:** **4–6 minutes of actual generation**, plus **3–8 minutes** of session setup (installing the CUDA build of `llama-cpp-python`, downloading the ~2 GB model, uploading the bundle). In practice: **about 8–14 minutes per session**, and a batch of 10 cases takes roughly 30–45 minutes total.

**Advantages**
- By far the biggest speed-up that costs nothing.
- Same model, same prompts, same validators — case quality is unchanged.
- GPU hours are enough for hundreds of cases per month.
- Can generate several cases in one session.

**Drawbacks**
- Requires internet, a Kaggle account, and moving files in and out.
- Sessions have time limits and can be queued or disconnected.
- Not part of the current one-command local flow; it is a separate batch workflow.

**Effect on players:** same quality of mystery, but new cases can be prepared ahead of time in minutes instead of waiting half an hour.
**Technical effect:** identical bundle format and validation. Generation simply runs elsewhere; the game itself stays the same.

*Free alternative to paid HF hosting:* a **free Hugging Face Space (CPU)** exists, but it gives about 2 slow CPU cores — **slower than this laptop**, so it does not help. Free Hugging Face serverless inference is not a reliable way to serve a custom 3B fine-tune. Kaggle is the realistic free replacement for a paid GPU endpoint.

---

### Option E — Use a free hosted API instead of the local model

**What it is:** generate the JSON with a free-tier hosted model (for example the Gemini free tier already used for NPC conversation, or Groq's free tier) instead of the local 3B model.

**Estimated time:** about **1–3 minutes per case**.

**Advantages**
- Fastest option, no local hardware needed.
- Makes use of the provider setup the game already has for conversation.
- No model files and no downloads.

**Drawbacks**
- **It is not your fine-tune.** Personality consistency and JSON reliability will differ, and more retries are likely.
- Internet, an API key, and free-tier rate limits apply; batch generation may be throttled.
- The game's design says case generation is local and offline. This changes that decision.
- Quality comparisons against the fine-tune become invalid.

**Effect on players:** cases appear almost instantly and vary more, but NPC personalities and secrets may be less consistent and more prone to odd wording.
**Technical effect:** needs a new adapter behind the existing model-runner interface. Validators stay, but pass rates and evaluation metrics change. Offline use becomes impossible.

---

### Option F — Pre-generate a library of cases

**Adopted:** the game ships curated cases in `bundles/library/` and lists them under **New Game → Play a Ready Case**, so those sessions start with no generation wait.

**What it is:** generate 5–10 finished bundles once, ship them with the game, and let the player pick one. Generation then takes **zero minutes during play**.

**Estimated time:** **0 minutes at play time**; 30–40 minutes per case if made on this laptop (or ~45 minutes total for 10 cases on a free Kaggle GPU).

**Advantages**
- Instant start, completely offline, no generation failures in front of a player.
- Perfect for demos and marking.
- The bundles are tiny (a few hundred KB each).

**Drawbacks**
- Limited replay value: after several sessions, players may see repeats.
- Not real procedural generation; new cases must be prepared in advance.

**Effect on players:** the game starts immediately, but case variety is fixed.
**Technical effect:** completely bypasses the generation pipeline. Bundles still go through the same validation, so the rest of the game is untouched.

---

### Option G — Use a smaller model (adopted as the 1B blueprint route)

**Adopted:** the fast route runs `Llama-3.2-1B-Instruct.Q4_K_M.gguf` to emit only the compact blueprint, and a deterministic compiler builds the full bundle. Because the small model no longer writes the full JSON, it needs a blueprint prompt rather than a full-bundle fine-tune, and case generation drops to seconds on CPU.

**What it is (general option):** run a smaller Qwen2.5 model in the same 4-bit format for the staged pipeline.

**Estimated time:** about **15–20 minutes** for the staged pipeline; **seconds** for the adopted blueprint route.

**Advantages**
- Free, offline, roughly twice as fast.
- Uses less memory, so the laptop stays responsive.

**Drawbacks**
- A 1.5B model for the staged pipeline would need its **own fine-tune** (the blueprint route instead uses the general 1B instruct model).
- Smaller models make more JSON mistakes and weaker logical connections between clues.

**Effect on players:** simpler, less surprising mysteries and flatter NPC personalities.
**Technical effect:** requires retraining, re-validation, and re-running the evaluation suite; likely more retries.

---

### Option H — Speculative decoding with a tiny draft model

**What it is:** a small 0.5B model guesses ahead and the 3B model checks the guesses.

**Estimated time:** about **20–30 minutes** (roughly 1.3–1.8× faster).

**Advantages**
- Free and fully offline.
- Output quality is normally unchanged.

**Drawbacks**
- Noticeable engineering effort and extra memory.
- Gains on a 4-core CPU are modest and inconsistent.
- `llama-cpp-python` support for draft models is fiddly to set up.

**Effect on players:** no visible change.
**Technical effect:** more moving parts in the runner; correctness depends on the draft model accepting the same tokenizer.

---

### Option I — Small housekeeping (threads and background load)

**What it is:** the runner currently uses "CPU cores minus one" (3 threads). Setting it to 4 and closing background applications can help slightly.

**Estimated time:** **28–36 minutes** (usually a few percent, never a big saving).

**Advantages**
- Free, one environment variable (`FABULA_MODEL_THREADS=4`), zero risk.

**Drawbacks**
- The laptop may feel sluggish while generating.
- Some CPUs are actually slower with all cores busy — measure, don't assume.

**Effect on players:** none worth mentioning.
**Technical effect:** none; the same pipeline runs slightly differently.

---

## 4. Side-by-side comparison

| Option | Free? | Estimated time (1 case) | Code or setup work | Case quality | Works offline |
| --- | --- | --- | --- | --- | --- |
| Current setup | — | 30–40 min | — | Baseline | Yes |
| A. Reuse prompt cache | Yes | 22–30 min | Small code change | Same | Yes |
| B. Shorter output budgets | Yes | 20–28 min | Small code change + testing | Slightly thinner writing | Yes |
| A + B together | Yes | **15–22 min** | Small code change + testing | Nearly the same | Yes |
| C. All NPCs in one call | Yes | 15–22 min | **Retraining required** | May improve consistency | Yes |
| D. Free Kaggle GPU | Yes | **8–14 min per session** (4–6 min generating) | Separate batch workflow | Same | No |
| E. Free hosted API | Yes (with limits) | **1–3 min** | New adapter | Different, less consistent | No |
| F. Pre-generated cases | Yes | **0 min at play** | Bundle library + picker | Same as the fine-tune | Yes |
| G. 1B blueprint model | Yes | **Instant** (adopted fast route; 15–20 min staged) | Fast route implemented | Blueprint-guided, simpler prose | Yes |
| H. Speculative decoding | Yes | 20–30 min | Complex code change | Same | Yes |
| I. Threads/background apps | Yes | 28–36 min | One environment variable | Same | Yes |

---

## 5. Recommended order

1. **Check the run report** for retries. If retries are happening, fix them first — it is free and can save the most time.
2. **Do A + B** (prompt reuse and tighter output budgets). Together they bring a case down to roughly **15–22 minutes** with no quality loss if the validators keep passing.
3. **Add F** (a small pre-generated library) so players and demos never wait at all.
4. **Use D** (free Kaggle GPU) when you need many fresh cases quickly. This is the only free route under five minutes per case.
5. Treat **C, E, and G** as research decisions, not quick fixes: each one changes the fine-tune or the project's offline design.

## 6. What will not help

- **Lowering `n_ctx`:** context size is not the bottleneck; generated tokens are.
- **More quantization:** the model is already Q4_K_M. Q3 saves a little memory but costs quality.
- **Ollama instead of llama.cpp:** same underlying engine on CPU, so the same speed.
- **Closing the game window while generating:** it does not compete for the CPU meaningfully; generation itself already uses every usable core.

## 7. How to verify any change

Run the same three seeds before and after, then compare, for each run:

- total elapsed seconds,
- generated tokens per stage,
- attempts per stage.

A change is only a win if total time drops **and** every stage still passes validation on the first attempt.

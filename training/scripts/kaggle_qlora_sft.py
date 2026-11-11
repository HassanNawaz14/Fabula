"""Kaggle T4 Unsloth QLoRA SFT Training & GGUF Export Script (Task D-02).

Fine-tunes Qwen2.5-3B-Instruct in 4-bit using Unsloth on train.jsonl (2,048 samples)
for 2 full epochs (512 steps). Exports LoRA adapters and merges to GGUF Q4_K_M
for local CPU game execution.

Features:
- Dynamic dataset path resolution (searches /kaggle/working and /kaggle/input)
- MAX_SEQ_LENGTH = 2560 (optimized memory footprint and attention throughput on T4)
- train_on_responses_only: cross-entropy loss computed strictly on assistant JSON completions
- Auto-resume checkpointing every 50 steps
- Merged 16-bit conversion and GGUF Q4_K_M export
"""

import glob
import json
import os

from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel
from unsloth.chat_templates import train_on_responses_only

# 1. Configuration
MAX_SEQ_LENGTH = 2560
MODEL_NAME = "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"
OUTPUT_DIR = "/kaggle/working/fabula_model_output"
ADAPTER_DIR = "/kaggle/working/fabula_qlora_adapter"
GGUF_DIR = "/kaggle/working/fabula_gguf"


def find_file(filename: str) -> str:
    """Dynamically search for dataset file across standard Kaggle and local paths."""
    candidates = [
        os.path.join("/kaggle/working", filename),
        os.path.join("data", "processed", filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # Search inside /kaggle/input (handles arbitrary dataset folder names)
    if os.path.exists("/kaggle/input"):
        for root, _, files in os.walk("/kaggle/input"):
            if filename in files:
                return os.path.join(root, filename)

    raise FileNotFoundError(
        f"Could not locate '{filename}'. Checked /kaggle/working, /kaggle/input, data/processed."
    )


def load_jsonl_messages(filepath: str, tokenizer) -> Dataset:
    """Read ChatML messages from JSONL and format with chat template."""
    data = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                formatted_text = tokenizer.apply_chat_template(
                    item["messages"],
                    tokenize=False,
                    add_generation_prompt=False,
                )
                data.append({"text": formatted_text})
    return Dataset.from_list(data)


def main():
    print(f"Loading Base Model: {MODEL_NAME} with max_seq_length={MAX_SEQ_LENGTH}...")

    # 2. Load Model & Tokenizer in 4-bit with Float16 for Tesla T4
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,  # Auto-select float16 on T4
        load_in_4bit=True,
    )

    # 3. Add Parameter-Efficient LoRA Adapters (Rank 16)
    target_modules = [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ]
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=target_modules,
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # 4. Prepare Datasets with dynamic path resolution
    train_path = find_file("train.jsonl")
    print(f"Found training set at: {train_path}")

    print("Formatting dataset into ChatML structure...")
    train_dataset = load_jsonl_messages(train_path, tokenizer)
    print(f"Train samples: {len(train_dataset)}")

    # 5. Trainer Configuration (2 full epochs, 512 steps, checkpoint every 50 steps)
    trainer_kwargs = {
        "model": model,
        "train_dataset": train_dataset,
        "dataset_text_field": "text",
        "max_seq_length": MAX_SEQ_LENGTH,
        "dataset_num_proc": 2,
        "packing": False,
        "args": TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=15,
            num_train_epochs=2,
            learning_rate=2e-4,
            fp16=True,
            logging_steps=25,
            eval_strategy="no",
            save_strategy="steps",
            save_steps=50,
            save_total_limit=2,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            seed=42,
            output_dir=OUTPUT_DIR,
            report_to="none",
        ),
    }

    try:
        trainer = SFTTrainer(processing_class=tokenizer, **trainer_kwargs)
    except TypeError:
        trainer = SFTTrainer(tokenizer=tokenizer, **trainer_kwargs)

    # 6. Response-Only Training: Mask prompt tokens so loss is computed solely on assistant JSON
    print("Applying response-only loss masking (training only on assistant completions)...")
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|im_start|>user\n",
        response_part="<|im_start|>assistant\n",
    )

    # 7. Check for existing checkpoint to resume from
    checkpoints = glob.glob(f"{OUTPUT_DIR}/checkpoint-*") if os.path.exists(OUTPUT_DIR) else []
    resume_checkpoint = None
    if checkpoints:
        checkpoints = sorted(
            checkpoints,
            key=lambda x: int(x.split("-")[-1]) if x.split("-")[-1].isdigit() else 0,
        )
        resume_checkpoint = checkpoints[-1]
        print(f"--> Found existing checkpoint! Resuming from {resume_checkpoint}...")
    else:
        print("--> Starting fresh training (512 steps)...")

    # 8. Start Training!
    print("\n" + "=" * 55)
    print("STARTING UNSLOTH QLORA TRAINING (2 EPOCHS, 512 STEPS)...")
    print("=" * 55)
    trainer_stats = trainer.train(resume_from_checkpoint=resume_checkpoint)
    runtime_mins = round(trainer_stats.metrics["train_runtime"] / 60, 1)
    print(f"\nTraining Finished in {runtime_mins} minutes!")

    # 9. Save LoRA Adapters
    print(f"\nSaving fine-tuned LoRA adapters to {ADAPTER_DIR}...")
    model.save_pretrained(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)

    # 10. Export to GGUF (Q4_K_M) for Local CPU Gameplay
    print(f"\nExporting GGUF model (Q4_K_M) to {GGUF_DIR}...")
    try:
        model.save_pretrained_gguf(
            GGUF_DIR,
            tokenizer,
            quantization_method="q4_k_m",
        )
        print("GGUF export successfully completed!")
    except Exception as e:
        print(f"GGUF direct export encountered an exception: {e}")
        print("Note: The LoRA adapter is fully saved and can be converted to GGUF anytime.")

    print("\n" + "=" * 55)
    print("ALL COMPLETE! Check /kaggle/working/ for output artifacts.")
    print("=" * 55)


if __name__ == "__main__":
    main()




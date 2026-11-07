"""Kaggle T4 Unsloth QLoRA SFT Training & GGUF Export Script (Task D-02).

Fine-tunes Qwen2.5-3B-Instruct in 4-bit using Unsloth on train.jsonl (2,048 samples)
and val.jsonl (256 samples) for 2 epochs. Exports LoRA adapters and merges to
GGUF Q4_K_M for local CPU game execution.

Total runtime: ~35-45 minutes on a single Kaggle Tesla T4 GPU.
"""

import json
import torch
from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel

# 1. Configuration
MAX_SEQ_LENGTH = 2048
MODEL_NAME = "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"
TRAIN_FILE = "/kaggle/working/train.jsonl"
VAL_FILE = "/kaggle/working/val.jsonl"
OUTPUT_DIR = "/kaggle/working/fabula_model_output"
ADAPTER_DIR = "/kaggle/working/fabula_qlora_adapter"
GGUF_DIR = "/kaggle/working/fabula_gguf"


def load_jsonl_messages(filepath: str, tokenizer) -> Dataset:
    """Read ChatML messages from JSONL and format with chat template."""
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
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
    print(f"Loading Base Model: {MODEL_NAME}...")

    # 2. Load Model & Tokenizer in 4-bit with Float16 for Tesla T4
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=True,
    )

    # 3. Add Parameter-Efficient LoRA Adapters (Rank 16)
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # 4. Prepare Datasets
    print("Formatting training & validation datasets...")
    train_dataset = load_jsonl_messages(TRAIN_FILE, tokenizer)
    val_dataset = load_jsonl_messages(VAL_FILE, tokenizer)
    print(f"Train samples: {len(train_dataset)} | Val samples: {len(val_dataset)}")

    # 5. Trainer Configuration
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_num_proc=2,
        packing=False,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=15,
            num_train_epochs=2,
            learning_rate=2e-4,
            fp16=True,
            logging_steps=25,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=42,
            output_dir=OUTPUT_DIR,
            report_to="none",
        ),
    )

    # 6. Start Training!
    print("\n" + "=" * 50)
    print("STARTING UNSLOTH QLORA TRAINING (2 EPOCHS)...")
    print("=" * 50)
    trainer_stats = trainer.train()
    print(f"\nTraining Finished in {round(trainer_stats.metrics['train_runtime'] / 60, 1)} minutes!")

    # 7. Save LoRA Adapters
    print(f"\nSaving fine-tuned LoRA adapters to {ADAPTER_DIR}...")
    model.save_pretrained(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)

    # 8. Export to GGUF (Q4_K_M) for Local CPU Gameplay
    print(f"\nExporting GGUF model (Q4_K_M) to {GGUF_DIR}...")
    model.save_pretrained_gguf(
        GGUF_DIR,
        tokenizer,
        quantization_method="q4_k_m",
    )

    print("\n" + "=" * 50)
    print("ALL COMPLETE! Model ready for local game inference.")
    print("=" * 50)


if __name__ == "__main__":
    main()


"""Kaggle T4 Unsloth Student QLoRA Fine-Tuning Script.

Fine-tunes an ultra-fast edge SLM (Llama-3.2-1B-Instruct) on 1,200 validated
Compact Blueprint DSL samples. Merges LoRA adapters and exports 4-bit GGUF Q4_K_M
for sub-5-second CPU case generation.

Target Hardware: Single Tesla T4 GPU (Kaggle)
Training Time: ~35 minutes
Output Size: ~750 MB GGUF
"""

import json
import os

from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel
from unsloth.chat_templates import train_on_responses_only

# 1. Configuration
MAX_SEQ_LENGTH = 1024
MODEL_NAME = "meta-llama/Llama-3.2-1B-Instruct"  # Or "unsloth/Qwen2.5-1.5B-Instruct-bnb-4bit"
OUTPUT_DIR = "/kaggle/working/fabula_student_output"
ADAPTER_DIR = "/kaggle/working/fabula_student_adapter"
GGUF_DIR = "/kaggle/working/fabula_student_gguf"


def find_file(filename: str) -> str:
    """Search for dataset file across standard Kaggle and local paths."""
    candidates = [
        os.path.join("/kaggle/working", filename),
        os.path.join("data", "processed", filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    if os.path.exists("/kaggle/input"):
        for root, _, files in os.walk("/kaggle/input"):
            if filename in files:
                return os.path.join(root, filename)

    raise FileNotFoundError(f"Could not locate '{filename}'.")


def load_dataset_from_jsonl(filepath: str, tokenizer) -> Dataset:
    """Format ChatML messages from JSONL for response-only loss computation."""
    data = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                formatted = tokenizer.apply_chat_template(
                    item["messages"],
                    tokenize=False,
                    add_generation_prompt=False,
                )
                data.append({"text": formatted})
    return Dataset.from_list(data)


def main():
    print(f"Loading Base Edge Model: {MODEL_NAME} with max_seq_length={MAX_SEQ_LENGTH}...")

    # 2. Load Model & Tokenizer in 4-bit with Float16 for Tesla T4
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,  # Auto-select float16 on T4
        load_in_4bit=True,
    )

    # 3. Add Parameter-Efficient LoRA Adapters (Rank 16)
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # 4. Load Train and Validation Splits
    train_file = find_file("blueprint_train.jsonl")
    train_dataset = load_dataset_from_jsonl(train_file, tokenizer)
    print(f"Loaded {len(train_dataset)} training examples from {train_file}.")

    # 5. Configure SFT Trainer with response-only loss
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=2,
        warmup_steps=20,
        num_train_epochs=2,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=25,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        save_strategy="no",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_num_proc=2,
        packing=False,
        args=training_args,
    )

    # Gradients computed strictly on assistant DSL completion
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|start_header_id|>user<|end_header_id|>\n\n",
        response_part="<|start_header_id|>assistant<|end_header_id|>\n\n",
    )

    # 6. Train Model
    print("Beginning Student Fine-Tuning on Kaggle T4...")
    trainer.train()
    print("Fine-tuning completed successfully!")

    # 7. Save LoRA Adapter
    os.makedirs(ADAPTER_DIR, exist_ok=True)
    model.save_pretrained(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)
    print(f"LoRA adapter saved to {ADAPTER_DIR}")

    # 8. Export Merged 4-bit Quantized GGUF for Local CPU Execution
    os.makedirs(GGUF_DIR, exist_ok=True)
    print(f"Exporting merged 4-bit Q4_K_M GGUF to {GGUF_DIR}...")
    model.save_pretrained_gguf(
        GGUF_DIR,
        tokenizer,
        quantization_method="q4_k_m",
    )
    print(f"GGUF artifact successfully exported to {GGUF_DIR}!")


if __name__ == "__main__":
    main()

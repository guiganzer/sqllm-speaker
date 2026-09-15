"""Executa SFT QLoRA para a fase 1 com logs e revisão de modelo imutáveis."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
from typing import Any

# O transporte HTTP é mais confiável para downloads grandes no Windows local.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from datasets import Dataset, load_dataset
from huggingface_hub import HfApi
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments


class CausalDataCollator:
    """Faz padding e preserva -100 para tokens que não devem contribuir à perda."""

    def __init__(self, pad_token_id: int) -> None:
        self.pad_token_id = pad_token_id

    def __call__(self, features: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
        longest = max(len(feature["input_ids"]) for feature in features)
        input_ids, attention_masks, labels = [], [], []
        for feature in features:
            padding = longest - len(feature["input_ids"])
            input_ids.append(feature["input_ids"] + [self.pad_token_id] * padding)
            attention_masks.append(feature["attention_mask"] + [0] * padding)
            labels.append(feature["labels"] + [-100] * padding)
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_masks, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def configure_logger(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("phase_01_training")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.StreamHandler(), logging.FileHandler(path, encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def tokenize_example(example: dict[str, Any], tokenizer: AutoTokenizer, max_sequence_length: int) -> dict[str, Any]:
    messages = example["messages"]
    prompt_ids = tokenizer.apply_chat_template(
        messages[:-1], tokenize=True, add_generation_prompt=True, return_dict=False
    )
    full_ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False, return_dict=False)
    if len(full_ids) > max_sequence_length or len(prompt_ids) >= len(full_ids):
        return {"keep": False, "input_ids": [], "attention_mask": [], "labels": []}
    return {
        "keep": True,
        "input_ids": full_ids,
        "attention_mask": [1] * len(full_ids),
        "labels": [-100] * len(prompt_ids) + full_ids[len(prompt_ids) :],
    }


def tokenize_dataset(
    dataset: Dataset,
    tokenizer: AutoTokenizer,
    max_sequence_length: int,
    requested_samples: int | None,
) -> Dataset:
    mapped = dataset.map(
        lambda example: tokenize_example(example, tokenizer, max_sequence_length),
        remove_columns=dataset.column_names,
        desc="Tokenizando exemplos",
    )
    accepted = mapped.filter(lambda example: example["keep"], desc="Removendo exemplos acima do limite").remove_columns("keep")
    if requested_samples is not None:
        return accepted.select(range(min(requested_samples, len(accepted))))
    return accepted


def load_jsonl(path: Path, requested_samples: int | None, candidate_factor: int) -> Dataset:
    dataset = load_dataset("json", data_files=str(path), split="train")
    if not isinstance(dataset, Dataset):
        raise TypeError("O JSONL deve carregar como Dataset")
    if requested_samples is not None:
        candidate_count = min(requested_samples * candidate_factor, len(dataset))
        dataset = dataset.select(range(candidate_count))
    return dataset


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default="Qwen/Qwen3-4B-Thinking-2507")
    parser.add_argument("--model-revision", default="main")
    parser.add_argument("--train-file", type=Path, default=Path("data/processed/phase-01/ee31747c93bd/train.jsonl"))
    parser.add_argument("--validation-file", type=Path, default=Path("data/processed/phase-01/ee31747c93bd/validation.jsonl"))
    parser.add_argument("--max-sequence-length", type=int, default=1024)
    parser.add_argument("--max-train-samples", type=int)
    parser.add_argument("--max-validation-samples", type=int)
    parser.add_argument(
        "--candidate-factor",
        type=int,
        default=64,
        help="Quantidade de candidatos por exemplo solicitado; exemplos longos são descartados sem truncamento.",
    )
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--run-name", default="phase-01")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA é obrigatória para este treino QLoRA local.")
    root = Path(__file__).resolve().parents[1]
    model_info = HfApi().model_info(arguments.model_id, revision=arguments.model_revision)
    model_revision = model_info.sha
    label = f"{arguments.run_name}-{model_revision[:12]}"
    logger = configure_logger(root / "artifacts" / "logs" / f"{label}.log")
    logger.info("Modelo %s revisao %s", arguments.model_id, model_revision)

    tokenizer = AutoTokenizer.from_pretrained(arguments.model_id, revision=model_revision)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    train = tokenize_dataset(
        load_jsonl(arguments.train_file, arguments.max_train_samples, arguments.candidate_factor),
        tokenizer,
        arguments.max_sequence_length,
        arguments.max_train_samples,
    )
    validation = tokenize_dataset(
        load_jsonl(arguments.validation_file, arguments.max_validation_samples, arguments.candidate_factor),
        tokenizer,
        arguments.max_sequence_length,
        arguments.max_validation_samples,
    )
    if not len(train) or not len(validation):
        raise SystemExit("Tokenização não produziu exemplos utilizáveis para treino e validação.")
    if arguments.max_train_samples is not None and len(train) < arguments.max_train_samples:
        raise SystemExit(f"Há somente {len(train)} exemplos de treino dentro do limite de contexto.")
    if arguments.max_validation_samples is not None and len(validation) < arguments.max_validation_samples:
        raise SystemExit(f"Há somente {len(validation)} exemplos de validação dentro do limite de contexto.")
    logger.info("Exemplos tokenizados: treino=%s validacao=%s", len(train), len(validation))

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        arguments.model_id,
        revision=model_revision,
        quantization_config=quantization,
        torch_dtype=torch.bfloat16,
        device_map={"": 0},
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    adapter = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, adapter)
    model.print_trainable_parameters()

    output_dir = root / "artifacts" / "runs" / label
    training_arguments = TrainingArguments(
        output_dir=str(output_dir),
        run_name=label,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=16,
        gradient_checkpointing=True,
        learning_rate=2e-4,
        num_train_epochs=arguments.epochs,
        max_steps=arguments.max_steps,
        # Transformers 5 representa uma razão de warmup como fração em warmup_steps.
        warmup_steps=0.03,
        logging_strategy="steps",
        logging_steps=1,
        eval_strategy="steps",
        eval_steps=5,
        save_strategy="steps",
        save_steps=5,
        save_total_limit=1,
        bf16=True,
        optim="paged_adamw_8bit",
        report_to=[],
        remove_unused_columns=False,
        seed=42,
    )
    trainer = Trainer(
        model=model,
        args=training_arguments,
        train_dataset=train,
        eval_dataset=validation,
        data_collator=CausalDataCollator(tokenizer.pad_token_id),
        processing_class=tokenizer,
    )
    train_metrics = trainer.train().metrics
    evaluation_metrics = trainer.evaluate()
    trainer.save_model()
    manifest = {
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "model_id": arguments.model_id,
        "model_revision": model_revision,
        "train_file": str(arguments.train_file),
        "validation_file": str(arguments.validation_file),
        "max_sequence_length": arguments.max_sequence_length,
        "max_steps": arguments.max_steps,
        "metrics": {"train": train_metrics, "evaluation": evaluation_metrics},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    logger.info("Treino concluido. Artefato: %s", output_dir)


if __name__ == "__main__":
    main()

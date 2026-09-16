"""Executa a especialização QLoRA Pagila preservando o adaptador concluído na fase 1."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import sys

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from datasets import Dataset, load_dataset
from peft import PeftModel, prepare_model_for_kbit_training
import torch
from train_phase_01 import CausalDataCollator, tokenize_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments


BASE_MODEL_ID = "Qwen/Qwen3-4B-Thinking-2507"
BASE_MODEL_REVISION = "768f209d9ea81521153ed38c47d515654e938aea"


def configure_logger(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("phase_02_pagila_training")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.StreamHandler(), logging.FileHandler(path, encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def load_jsonl(path: Path, requested_samples: int | None, seed: int) -> Dataset:
    dataset = load_dataset("json", data_files=str(path), split="train")
    if not isinstance(dataset, Dataset):
        raise TypeError("O JSONL deve carregar como Dataset.")
    if requested_samples is not None:
        dataset = dataset.shuffle(seed=seed).select(range(min(requested_samples, len(dataset))))
    return dataset


def parse_arguments() -> argparse.Namespace:
    default_corpus = Path("data/processed/phase-02/pagila-v18-fc7a867-pt-v1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default=BASE_MODEL_ID)
    parser.add_argument("--model-revision", default=BASE_MODEL_REVISION)
    parser.add_argument(
        "--initial-adapter",
        type=Path,
        default=Path("artifacts/runs/phase-01-general-e1-768f209d9ea8"),
        help="Adaptador da fase 1; é continuado, nunca substituído por um LoRA novo.",
    )
    parser.add_argument("--train-file", type=Path, default=default_corpus / "train.jsonl")
    parser.add_argument("--validation-file", type=Path, default=default_corpus / "validation.jsonl")
    parser.add_argument("--max-sequence-length", type=int, default=1024)
    parser.add_argument("--max-train-samples", type=int)
    parser.add_argument("--max-validation-samples", type=int)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--run-name", default="phase-02-pagila-v1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--logging-steps", type=int, default=5)
    parser.add_argument("--eval-steps", type=int, default=20)
    parser.add_argument("--save-steps", type=int, default=20)
    parser.add_argument("--save-total-limit", type=int, default=3)
    parser.add_argument("--resume-from-checkpoint", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA é obrigatória para este treino QLoRA local.")
    if arguments.model_id != BASE_MODEL_ID or arguments.model_revision != BASE_MODEL_REVISION:
        raise SystemExit("A fase 2 requer a mesma revisão imutável usada na fase 1.")
    initial_adapter = (ROOT / arguments.initial_adapter).resolve() if not arguments.initial_adapter.is_absolute() else arguments.initial_adapter
    if not (initial_adapter / "adapter_config.json").is_file():
        raise SystemExit(f"Adaptador inicial não encontrado ou incompleto: {initial_adapter}")

    label = f"{arguments.run_name}-{arguments.model_revision[:12]}"
    output_dir = ROOT / "artifacts" / "runs" / label
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = configure_logger(ROOT / "artifacts" / "logs" / f"{label}.log")
    running_manifest = output_dir / "running-manifest.json"
    running_manifest.write_text(
        json.dumps(
            {
                "started_at_utc": datetime.now(UTC).isoformat(),
                "status": "running",
                "model_id": arguments.model_id,
                "model_revision": arguments.model_revision,
                "initial_adapter": str(initial_adapter),
                "arguments": vars(arguments),
            },
            default=str,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    tokenizer = AutoTokenizer.from_pretrained(arguments.model_id, revision=arguments.model_revision)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    train = tokenize_dataset(load_jsonl(arguments.train_file, arguments.max_train_samples, arguments.seed), tokenizer, arguments.max_sequence_length, arguments.max_train_samples)
    validation = tokenize_dataset(load_jsonl(arguments.validation_file, arguments.max_validation_samples, arguments.seed), tokenizer, arguments.max_sequence_length, arguments.max_validation_samples)
    if not len(train) or not len(validation):
        raise SystemExit("Tokenização não produziu exemplos utilizáveis para treino e validação.")
    logger.info("Exemplos tokenizados: treino=%s validacao=%s", len(train), len(validation))

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        arguments.model_id,
        revision=arguments.model_revision,
        quantization_config=quantization,
        dtype=torch.bfloat16,
        device_map={"": 0},
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = PeftModel.from_pretrained(model, str(initial_adapter), is_trainable=True)
    model.print_trainable_parameters()

    training_arguments = TrainingArguments(
        output_dir=str(output_dir),
        run_name=label,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=16,
        gradient_checkpointing=True,
        learning_rate=arguments.learning_rate,
        num_train_epochs=arguments.epochs,
        max_steps=arguments.max_steps,
        warmup_steps=0.03,
        logging_strategy="steps",
        logging_steps=arguments.logging_steps,
        eval_strategy="steps",
        eval_steps=arguments.eval_steps,
        save_strategy="steps",
        save_steps=arguments.save_steps,
        save_total_limit=arguments.save_total_limit,
        bf16=True,
        optim="paged_adamw_8bit",
        report_to=[],
        remove_unused_columns=False,
        seed=arguments.seed,
    )
    trainer = Trainer(
        model=model,
        args=training_arguments,
        train_dataset=train,
        eval_dataset=validation,
        data_collator=CausalDataCollator(tokenizer.pad_token_id),
        processing_class=tokenizer,
    )
    train_metrics = trainer.train(resume_from_checkpoint=str(arguments.resume_from_checkpoint) if arguments.resume_from_checkpoint else None).metrics
    evaluation_metrics = trainer.evaluate()
    trainer.save_model()
    manifest = {
        "status": "completed",
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "model_id": arguments.model_id,
        "model_revision": arguments.model_revision,
        "initial_adapter": str(initial_adapter),
        "train_file": str(arguments.train_file),
        "validation_file": str(arguments.validation_file),
        "train_examples": len(train),
        "validation_examples": len(validation),
        "max_sequence_length": arguments.max_sequence_length,
        "arguments": vars(arguments),
        "metrics": {"train": train_metrics, "evaluation": evaluation_metrics},
    }
    running_manifest.write_text(json.dumps(manifest, default=str, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    running_manifest.replace(output_dir / "run-manifest.json")
    logger.info("Treino concluído. Artefato: %s", output_dir)


if __name__ == "__main__":
    main()

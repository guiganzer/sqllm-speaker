"""Gera SQL em validação isolada e mede conformidade estrutural da fase 1."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Any

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from datasets import load_dataset
from peft import PeftModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_to_sql.evaluation import (
    aggregate_assessments,
    assess_sql,
    canonical_sql,
    complexity_bucket,
    deterministic_stratified_sample,
    normalize_model_output,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default="Qwen/Qwen3-4B-Thinking-2507")
    parser.add_argument("--model-revision", default="768f209d9ea81521153ed38c47d515654e938aea")
    parser.add_argument("--adapter-path", type=Path, help="Diretório do adapter LoRA. Omitir para medir o modelo-base.")
    parser.add_argument("--validation-file", type=Path, default=Path("data/processed/phase-01/ee31747c93bd/validation.jsonl"))
    parser.add_argument("--sample-size", type=int, default=512)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--batch-size", type=int, default=4, help="Número de prompts por geração; 4 é seguro para 8 GiB de VRAM.")
    parser.add_argument("--run-name", default="phase-01-evaluation")
    return parser.parse_args()


def load_model(model_id: str, revision: str, adapter_path: Path | None):
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        revision=revision,
        quantization_config=quantization,
        dtype=torch.bfloat16,
        device_map={"": 0},
    )
    if adapter_path:
        model = PeftModel.from_pretrained(model, str(adapter_path))
    model.eval()
    return model, tokenizer


def render_prompt(tokenizer, messages: list[dict[str, str]]) -> str:
    try:
        return tokenizer.apply_chat_template(messages[:-1], enable_thinking=False, tokenize=False, add_generation_prompt=True)
    except TypeError:
        return tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True)


def generate_sql_batch(model, tokenizer, conversations: list[list[dict[str, str]]], max_new_tokens: int) -> list[str]:
    prompts = [render_prompt(tokenizer, messages) for messages in conversations]
    original_padding_side = tokenizer.padding_side
    tokenizer.padding_side = "left"
    encoded = tokenizer(prompts, return_tensors="pt", padding=True)
    tokenizer.padding_side = original_padding_side
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    with torch.inference_mode():
        generated = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    prompt_length = encoded["input_ids"].shape[1]
    return [tokenizer.decode(row[prompt_length:], skip_special_tokens=True).strip() for row in generated]


def main() -> None:
    arguments = parse_arguments()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA é obrigatória para avaliação local deste modelo.")
    root = Path(__file__).resolve().parents[1]
    dataset = load_dataset("json", data_files=str(arguments.validation_file), split="train")
    records = deterministic_stratified_sample([dataset[index] for index in range(len(dataset))], arguments.sample_size)
    if len(records) < arguments.sample_size:
        raise SystemExit(f"A validação só possui {len(records)} exemplos para a amostra solicitada.")
    model, tokenizer = load_model(arguments.model_id, arguments.model_revision, arguments.adapter_path)

    rows: list[dict[str, Any]] = []
    assessments = []
    exact_matches: list[bool] = []
    for start in range(0, len(records), arguments.batch_size):
        batch = records[start : start + arguments.batch_size]
        raw_outputs = generate_sql_batch(model, tokenizer, [record["messages"] for record in batch], arguments.max_new_tokens)
        for index, (record, raw_output) in enumerate(zip(batch, raw_outputs), start=start + 1):
            generated = normalize_model_output(raw_output)
            ddl = record["messages"][1]["content"].split("</schema>", maxsplit=1)[0].removeprefix("<schema>\n")
            assessment = assess_sql(generated, ddl)
            assessments.append(assessment)
            exact_match = canonical_sql(generated) == canonical_sql(record["messages"][-1]["content"])
            exact_matches.append(exact_match)
            rows.append(
                {
                    "index": index,
                    "schema_group": record["schema_group"],
                    "complexity": complexity_bucket(record["messages"][-1]["content"]),
                    "question": record["messages"][1]["content"],
                    "reference_sql": record["messages"][-1]["content"],
                    "raw_output": raw_output,
                    "generated_sql": generated,
                    "exact_match": exact_match,
                    "assessment": assessment.__dict__,
                }
            )
            print(f"[{index}/{len(records)}] parse={assessment.parses} schema={assessment.schema_references_valid}", flush=True)

    output_dir = root / "artifacts" / "evaluations" / arguments.run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = aggregate_assessments(assessments)
    metrics["exact_match_count"] = sum(exact_matches)
    metrics["exact_match_rate"] = sum(exact_matches) / len(exact_matches)
    report = {
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "model_id": arguments.model_id,
        "model_revision": arguments.model_revision,
        "adapter_path": str(arguments.adapter_path) if arguments.adapter_path else None,
        "sample_size": arguments.sample_size,
        "max_new_tokens": arguments.max_new_tokens,
        "metrics": metrics,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (output_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

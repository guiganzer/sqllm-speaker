"""Executa jobs de mensagens com um modelo Hugging Face local, com retomada por ID."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from peft import PeftModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


BASE_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
BASE_MODEL_REVISION = "e7974da369bd887ad4f10a072ec4f933ac5391bf"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-id", default=BASE_MODEL_ID)
    parser.add_argument("--model-revision", default=BASE_MODEL_REVISION)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--max-jobs", type=int)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    identifiers = [str(record.get("id", "")) for record in records]
    if not all(identifiers) or len(identifiers) != len(set(identifiers)):
        raise ValueError(f"Jobs com IDs ausentes ou repetidos: {path}")
    return records


def _completed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    completed: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Saída corrompida na linha {number}: {path}") from error
        completed.add(str(record["id"]))
    return completed


def main() -> None:
    arguments = parse_arguments()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA é obrigatória para a geração local.")
    if arguments.max_jobs is not None and arguments.max_jobs < 1:
        raise SystemExit("--max-jobs deve ser positivo.")
    jobs = _read_jsonl(arguments.jobs)
    completed = _completed_ids(arguments.output)
    pending = [job for job in jobs if str(job["id"]) not in completed]
    if arguments.max_jobs is not None:
        pending = pending[: arguments.max_jobs]
    if not pending:
        print("Nenhum job pendente.")
        return

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(arguments.model_id, revision=arguments.model_revision)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        arguments.model_id,
        revision=arguments.model_revision,
        quantization_config=quantization,
        dtype=torch.bfloat16,
        device_map={"": 0},
    )
    if arguments.adapter:
        if not (arguments.adapter / "adapter_config.json").is_file():
            raise SystemExit(f"Adapter inválido: {arguments.adapter}")
        model = PeftModel.from_pretrained(model, str(arguments.adapter), is_trainable=False)
    model.eval()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("a", encoding="utf-8", newline="\n") as output_handle:
        for offset, job in enumerate(pending):
            messages = job.get("messages")
            if not isinstance(messages, list):
                raise ValueError(f"Job sem messages: {job['id']}")
            try:
                prompt = tokenizer.apply_chat_template(
                    messages,
                    enable_thinking=False,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except TypeError:
                prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            encoded = tokenizer(prompt, return_tensors="pt")
            encoded = {key: value.to(model.device) for key, value in encoded.items()}
            generation: dict[str, object] = {
                "max_new_tokens": arguments.max_new_tokens,
                "do_sample": arguments.temperature > 0,
                "pad_token_id": tokenizer.pad_token_id,
            }
            if arguments.temperature > 0:
                generation.update({"temperature": arguments.temperature, "top_p": arguments.top_p})
            torch.manual_seed(arguments.seed + offset)
            with torch.inference_mode():
                generated = model.generate(**encoded, **generation)
            prompt_length = encoded["input_ids"].shape[1]
            response = tokenizer.decode(generated[0, prompt_length:], skip_special_tokens=True).strip()
            record = {
                "id": job["id"],
                "response": response,
                "model_id": arguments.model_id,
                "model_revision": arguments.model_revision,
                "adapter": str(arguments.adapter) if arguments.adapter else None,
                "seed": arguments.seed + offset,
            }
            output_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            output_handle.flush()
            print(f"{offset + 1}/{len(pending)} {job['id']}", flush=True)


if __name__ == "__main__":
    main()

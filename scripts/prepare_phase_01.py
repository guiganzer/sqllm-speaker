"""Prepara dados públicos de português para SQL de forma reprodutível."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from datasets import Dataset, load_dataset
from huggingface_hub import HfApi
from sqlglot import parse
from sqlglot.errors import ParseError


SYSTEM_PROMPT = (
    "Você é um assistente especializado em SQL. Gere somente uma consulta SQL "
    "compatível com o schema fornecido. Não explique a resposta."
)
REQUIRED_FIELDS = ("pergunta", "contexto", "resposta")


@dataclass(frozen=True)
class PreparationSettings:
    dataset_id: str
    requested_revision: str
    validation_percent: int
    max_characters: int
    root_dir: Path


@dataclass
class PreparationReport:
    dataset_id: str
    requested_revision: str
    resolved_revision: str
    retrieved_at_utc: str
    source_rows: int
    accepted_rows: int
    train_rows: int
    validation_rows: int
    schema_groups: int
    rejected: dict[str, int]
    raw_path: str
    processed_path: str


def normalize_question(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_sql_or_ddl(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize_record(row: Mapping[str, Any], max_characters: int) -> tuple[dict[str, str] | None, str | None]:
    if any(not isinstance(row.get(field), str) or not row[field].strip() for field in REQUIRED_FIELDS):
        return None, "missing_required_field"

    question = normalize_question(row["pergunta"])
    schema = normalize_sql_or_ddl(row["contexto"])
    sql = normalize_sql_or_ddl(row["resposta"])
    if max(len(question), len(schema), len(sql)) > max_characters:
        return None, "exceeds_character_limit"
    try:
        expressions = parse(sql)
    except ParseError:
        return None, "invalid_sql"
    if len(expressions) != 1:
        return None, "multiple_sql_statements"
    return {"question": question, "schema": schema, "sql": sql}, None


def schema_group(schema: str) -> str:
    return sha256(schema.encode("utf-8")).hexdigest()


def record_key(record: Mapping[str, str]) -> str:
    material = "\x1f".join((record["question"], record["schema"], record["sql"]))
    return sha256(material.encode("utf-8")).hexdigest()


def is_validation_group(group: str, validation_percent: int) -> bool:
    return int(group[:8], 16) % 100 < validation_percent


def to_training_example(record: Mapping[str, str], source: Mapping[str, str]) -> dict[str, Any]:
    user = f"<schema>\n{record['schema']}\n</schema>\n\n<pergunta>\n{record['question']}\n</pergunta>"
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": record["sql"]},
        ],
        "schema_group": schema_group(record["schema"]),
        "source": dict(source),
    }


def prepare_examples(
    rows: Iterable[Mapping[str, Any]], *, validation_percent: int, max_characters: int, source: Mapping[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str], int]:
    if not 1 <= validation_percent <= 50:
        raise ValueError("validation_percent deve estar entre 1 e 50")
    rejected: Counter[str] = Counter()
    seen: set[str] = set()
    schema_groups: set[str] = set()
    train: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []

    for row in rows:
        normalized, reason = normalize_record(row, max_characters)
        if reason:
            rejected[reason] += 1
            continue
        assert normalized is not None
        key = record_key(normalized)
        if key in seen:
            rejected["duplicate"] += 1
            continue
        seen.add(key)
        group = schema_group(normalized["schema"])
        schema_groups.add(group)
        example = to_training_example(normalized, source)
        if is_validation_group(group, validation_percent):
            validation.append(example)
        else:
            train.append(example)
    return train, validation, rejected, len(schema_groups)


def write_jsonl(path: Path, examples: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        for example in examples:
            output.write(json.dumps(example, ensure_ascii=False, sort_keys=True))
            output.write("\n")


def prepare_dataset(settings: PreparationSettings) -> PreparationReport:
    api = HfApi()
    info = api.dataset_info(settings.dataset_id, revision=settings.requested_revision)
    resolved_revision = info.sha
    dataset = load_dataset(settings.dataset_id, revision=resolved_revision, split="train")
    if not isinstance(dataset, Dataset):
        raise TypeError("A fonte deve carregar um split único do tipo Dataset")

    root = settings.root_dir
    safe_name = settings.dataset_id.replace("/", "__")
    revision_label = resolved_revision[:12]
    raw_path = root / "data" / "raw" / safe_name / revision_label
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_path.exists():
        dataset.save_to_disk(str(raw_path))

    source = {"dataset_id": settings.dataset_id, "revision": resolved_revision}
    train, validation, rejected, group_count = prepare_examples(
        dataset,
        validation_percent=settings.validation_percent,
        max_characters=settings.max_characters,
        source=source,
    )
    processed_path = root / "data" / "processed" / "phase-01" / revision_label
    if processed_path.exists():
        raise FileExistsError(f"Saída já existe: {processed_path}. Escolha outra revisão ou remova-a conscientemente.")
    processed_path.mkdir(parents=True)
    write_jsonl(processed_path / "train.jsonl", train)
    write_jsonl(processed_path / "validation.jsonl", validation)

    report = PreparationReport(
        dataset_id=settings.dataset_id,
        requested_revision=settings.requested_revision,
        resolved_revision=resolved_revision,
        retrieved_at_utc=datetime.now(UTC).isoformat(),
        source_rows=len(dataset),
        accepted_rows=len(train) + len(validation),
        train_rows=len(train),
        validation_rows=len(validation),
        schema_groups=group_count,
        rejected=dict(sorted(rejected.items())),
        raw_path=str(raw_path.relative_to(root)),
        processed_path=str(processed_path.relative_to(root)),
    )
    reports_dir = root / "artifacts" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"phase-01-data-{revision_label}.json"
    with report_path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(asdict(report), output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    return report


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", default="emdemor/sql-create-context-pt")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--validation-percent", type=int, default=10)
    parser.add_argument("--max-characters", type=int, default=16_000)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    settings = PreparationSettings(
        dataset_id=arguments.dataset_id,
        requested_revision=arguments.revision,
        validation_percent=arguments.validation_percent,
        max_characters=arguments.max_characters,
        root_dir=Path(__file__).resolve().parents[1],
    )
    report = prepare_dataset(settings)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

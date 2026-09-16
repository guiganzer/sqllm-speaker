"""Inspeciona e fixa o subconjunto Sakila do benchmark externo Text-to-SQL."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "fab6e4d40da5f58dd42fe5072a01ca6305835d88"
DEFAULT_SOURCE = ROOT / "data" / "raw" / "text2sql-benchmark-id" / SOURCE_REVISION[:12] / "gold-standard.json"
ID_PATTERN = re.compile(r"^SAK-[A-Z]\d-\d{2}$")


@dataclass(frozen=True)
class ExternalSakilaRecord:
    identifier: str
    category: str
    question_indonesian: str
    question_english: str
    sql_mysql: str
    expected_rows: tuple[dict[str, Any], ...]
    ordering: str | None


def load_sakila_records(path: Path) -> list[ExternalSakilaRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("gold-standard.json deve conter uma lista.")
    records: list[ExternalSakilaRecord] = []
    seen: set[str] = set()
    for row in payload:
        if not isinstance(row, dict) or row.get("db") != "sakila":
            continue
        identifier = row.get("id")
        category = row.get("category")
        question_id = row.get("question_id")
        question_en = row.get("question_en")
        sql = row.get("solution_sql")
        expected_rows = row.get("expected_rows")
        if not all(isinstance(value, str) and value.strip() for value in (identifier, category, question_id, question_en, sql)):
            raise ValueError(f"Item Sakila incompleto: {identifier!r}.")
        if not ID_PATTERN.fullmatch(identifier) or identifier in seen:
            raise ValueError(f"ID Sakila inválido ou duplicado: {identifier!r}.")
        if not isinstance(expected_rows, list) or not all(isinstance(item, dict) for item in expected_rows):
            raise ValueError(f"expected_rows inválido: {identifier}.")
        seen.add(identifier)
        records.append(
            ExternalSakilaRecord(
                identifier=identifier,
                category=category,
                question_indonesian=question_id,
                question_english=question_en,
                sql_mysql=sql,
                expected_rows=tuple(expected_rows),
                ordering=row.get("ordering"),
            )
        )
    if len(records) != 30:
        raise ValueError(f"Esperados 30 itens Sakila, encontrados {len(records)}.")
    return sorted(records, key=lambda record: record.identifier)


def summarize(path: Path, records: list[ExternalSakilaRecord]) -> dict[str, Any]:
    categories = Counter(record.category for record in records)
    ids = "\n".join(record.identifier for record in records).encode("utf-8")
    return {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "repository": "https://github.com/Galih-Hermawan-Unikom/text2sql-benchmark-id",
            "revision": SOURCE_REVISION,
            "license": "MIT",
            "gold_standard_sha256": sha256(path.read_bytes()).hexdigest(),
        },
        "subset": {
            "database": "sakila",
            "items": len(records),
            "categories": dict(sorted(categories.items())),
            "ids_sha256": sha256(ids).hexdigest(),
            "question_languages": ["id", "en"],
            "sql_dialect": "mysql",
            "expected_rows_provided": True,
        },
        "governance": {
            "allowed_for_training": False,
            "allowed_for_current_pagila_benchmark": False,
            "port_to_pagila_without_separate_derivation": False,
            "purpose": "Validação externa de terceiros; a execução canônica deve usar o schema e dialeto Sakila da fonte.",
        },
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    records = load_sakila_records(arguments.source)
    report = summarize(arguments.source, records)
    if arguments.report:
        if arguments.report.exists():
            raise FileExistsError(f"Relatório já existe: {arguments.report}")
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
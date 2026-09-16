"""Cria uma suíte externa derivada, com SQL Sakila/MySQL transposto e executado no Pagila/PostgreSQL."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.pagila_tools import PagilaAgentTools
from scripts.inspect_external_sakila_benchmark import DEFAULT_SOURCE, SOURCE_REVISION, load_sakila_records
from sqlglot import parse_one, transpile
from sqlglot.errors import ParseError


def transpile_mysql_to_postgres(sql: str) -> str:
    """Transpõe uma única consulta de referência sem editar sua intenção manualmente."""

    try:
        candidates = transpile(sql, read="mysql", write="postgres", identity=False)
    except ParseError as error:
        raise ValueError("SQL MySQL não fez parse para transpilar.") from error
    if len(candidates) != 1:
        raise ValueError("A transpilação deve produzir exatamente uma consulta PostgreSQL.")
    translated = candidates[0].strip()
    try:
        parse_one(translated, read="postgres")
    except ParseError as error:
        raise ValueError("SQL transposto não fez parse como PostgreSQL.") from error
    return translated


def apply_pagila_compatibility(identifier: str, sql: str) -> str:
    """Aplica equivalências revisadas entre o Sakila original e o Pagila v18."""

    if identifier in {"SAK-J2-01", "SAK-J2-04", "SAK-J2-05"}:
        sql = re.sub(r'\br\.(?:"rental_date"|rental_date)', "LOWER(r.rental_period)", sql)
    if identifier == "SAK-S6-02":
        sql = sql.replace("FROM film HAVING length =", "FROM film WHERE length =")
    return sql


def rows_hash(rows: tuple[tuple[str, ...], ...]) -> str:
    return sha256("\n".join("\t".join(row) for row in rows).encode("utf-8")).hexdigest()


def port_records(source: Path, output: Path, *, max_rows: int = 1_000) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Saída já existe: {output}")
    records = load_sakila_records(source)
    output.mkdir(parents=True)
    tools = PagilaAgentTools()
    accepted = 0
    rejected: Counter[str] = Counter()
    serialized: list[dict[str, Any]] = []
    for source_record in records:
        row: dict[str, Any] = {
            "id": source_record.identifier,
            "category": source_record.category,
            "question_id": source_record.question_indonesian,
            "question_en": source_record.question_english,
            "source_sql_mysql": source_record.sql_mysql,
            "postgres_sql": None,
            "execution_accepted": False,
            "result_rows": None,
            "result_sha256": None,
            "reason": None,
        }
        try:
            translated = apply_pagila_compatibility(source_record.identifier, transpile_mysql_to_postgres(source_record.sql_mysql))
            row["postgres_sql"] = translated
            execution = tools.execute_readonly_sql(translated, max_rows=max_rows)
            if not execution.approved:
                row["reason"] = f"policy: {execution.reason}"
                rejected["policy"] += 1
            elif execution.error:
                row["reason"] = f"execution: {execution.error}"
                rejected["execution"] += 1
            elif execution.truncated:
                row["reason"] = "execution: resultado excede max_rows"
                rejected["truncated"] += 1
            else:
                row["execution_accepted"] = True
                row["result_rows"] = len(execution.rows)
                row["result_sha256"] = rows_hash(execution.rows)
                accepted += 1
        except ValueError as error:
            row["reason"] = f"transpile: {error}"
            rejected["transpile"] += 1
        serialized.append(row)
    with (output / "derived.jsonl").open("x", encoding="utf-8", newline="\n") as file:
        for row in serialized:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            file.write("\n")
    report = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "repository": "https://github.com/Galih-Hermawan-Unikom/text2sql-benchmark-id",
            "revision": SOURCE_REVISION,
            "gold_standard_sha256": sha256(source.read_bytes()).hexdigest(),
            "license": "MIT",
        },
        "derivation": {
            "input_dialect": "mysql",
            "output_dialect": "postgres",
            "runtime": "Pagila PostgreSQL local via sqllm_readonly",
            "method": "sqlglot transpile(mysql -> postgres), seguida por quatro mapeamentos de equivalência Pagila v18 revisados e execução",
            "compatibility_mappings": {"rental_date": "LOWER(rental_period) em SAK-J2-01/J2-04/J2-05", "having_without_group": "WHERE em SAK-S6-02"},
            "expected_rows_original_used_as_pagila_oracle": False,
            "allowed_for_training": False,
        },
        "total_external_items": len(records),
        "execution_accepted": accepted,
        "rejected": dict(sorted(rejected.items())),
        "output": str(output.relative_to(ROOT)),
    }
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--label", default="sakila-third-party-fab6e4d40da5-pg-v3")
    parser.add_argument("--max-rows", type=int, default=1_000)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    output = ROOT / "data" / "evaluations" / "external" / arguments.label
    report = port_records(arguments.source, output, max_rows=arguments.max_rows)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
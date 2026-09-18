"""Gera o corpus PT-BR Olist v1 e valida toda SQL no espelho SQLite read-only."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.prompt_specializer import PromptTemplate, build_schema_fk_messages
from llm_to_sql.agentic.sqlite_validator import SqliteCatalogValidator
from llm_to_sql.olist_corpus import build_specs
from llm_to_sql.schema_catalog import SchemaCatalog


VALIDATION_FAMILIES = frozenset(
    {
        "olist-payment-status-total",
        "olist-customer-review-payment",
        "olist-heavy-negative-commerce",
    }
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "configs" / "datasets" / "olist.json")
    parser.add_argument("--prompt", type=Path, default=ROOT / "configs" / "prompts" / "sql-author-schema-fk-v1.json")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "interim" / "olist-validation.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "processed" / "phase-04" / "olist-public-pt-v1")
    return parser.parse_args()


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for record in records:
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
            handle.write(line + "\n")
            digest.update((line + "\n").encode("utf-8"))
    return digest.hexdigest()


def generate(catalog_path: Path, prompt_path: Path, database: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"Saída já existe: {output}")
    catalog = SchemaCatalog.load(catalog_path)
    prompt = PromptTemplate.load(prompt_path)
    validator = SqliteCatalogValidator(
        catalog=catalog,
        database_path=database,
        max_virtual_machine_steps=500_000_000,
    )
    connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    try:
        specs = build_specs(connection)
    finally:
        connection.close()
    records: list[dict[str, object]] = []
    seen_questions: set[str] = set()
    seen_sql: set[str] = set()
    for spec in specs:
        question_key = " ".join(spec.question.casefold().split())
        if question_key in seen_questions or spec.sql in seen_sql:
            raise RuntimeError(f"Exemplo duplicado: {spec.identifier}")
        seen_questions.add(question_key)
        seen_sql.add(spec.sql)
        result = validator.validate_and_execute(spec.sql, pack_name=spec.pack, max_rows=10)
        if not result.approved or not result.executed:
            raise RuntimeError(f"SQL inválida em {spec.identifier}: {result.error or result.reason}")
        messages = build_schema_fk_messages(
            question=spec.question,
            catalog=catalog,
            pack_name=spec.pack,
            template=prompt,
        )
        messages.append({"role": "assistant", "content": spec.sql})
        records.append(
            {
                "id": spec.identifier,
                "source": "olist-original-public",
                "language": "pt-BR",
                "dialect": "sqlite",
                "family": spec.family,
                "tier": spec.tier,
                "relation_pack": spec.pack,
                "question": spec.question,
                "sql": spec.sql,
                "messages": messages,
                "execution_validated": True,
                "training_ready": True,
            }
        )
    train = [record for record in records if record["family"] not in VALIDATION_FAMILIES]
    validation = [record for record in records if record["family"] in VALIDATION_FAMILIES]
    output.mkdir(parents=True)
    train_hash = _write_jsonl(output / "train.jsonl", train)
    validation_hash = _write_jsonl(output / "validation.jsonl", validation)
    tier_counts = Counter(str(record["tier"]) for record in records)
    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "id": "olist-public-pt-v1",
        "status": "validated",
        "training_ready": True,
        "source": "olist-original-public",
        "database": str(database),
        "prompt_id": prompt.identifier,
        "split_strategy": "held_out_families",
        "validation_families": sorted(VALIDATION_FAMILIES),
        "train_examples": len(train),
        "validation_examples": len(validation),
        "tier_counts": dict(sorted(tier_counts.items())),
        "train_sha256": train_hash,
        "validation_sha256": validation_hash,
    }
    (output / "corpus-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    arguments = parse_arguments()
    print(
        json.dumps(
            generate(arguments.catalog, arguments.prompt, arguments.database, arguments.output),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

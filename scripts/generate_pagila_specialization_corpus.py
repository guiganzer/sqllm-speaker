"""Gera e valida os corpora públicos Pagila para especialização incremental."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.context_compiler import compile_schema_context
from llm_to_sql.agentic.pagila_tools import PagilaAgentTools
from llm_to_sql.phase_02 import SYSTEM_PROMPT, build_specs, canonical_sql, corpus_fingerprint


# A divisão é por família: uma mesma estrutura de SQL não chega a treino e validação.
VALIDATION_FAMILIES_BY_EDITION = {
    "v1": frozenset({"actor-letter", "payment-amount-bands", "rental-duration"}),
    "v2": frozenset(
        {
            "actor-letter",
            "payment-amount-bands",
            "rental-duration",
            "staff-payment-left",
            "rental-by-day",
            "customer-list-country-view",
        }
    ),
    "v3": frozenset(
        {
            "v3-actor-prefix-rating",
            "v3-rental-day-store",
            "v3-category-revenue-top",
        }
    ),
}


def _messages(context: str, question: str, sql: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"<schema>\n{context}\n</schema>\n<pergunta>\n{question}\n</pergunta>"},
        {"role": "assistant", "content": sql},
    ]


def _internal_benchmark_sets() -> tuple[set[str], set[str]]:
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from generate_pagila_evaluation import build_specs as build_internal_benchmark

    internal = build_internal_benchmark()
    return (
        {" ".join(spec.question.lower().split()) for spec in internal},
        {canonical_sql(spec.sql) for spec in internal},
    )


def build_records(tools: PagilaAgentTools, *, edition: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    internal_questions, internal_sql = _internal_benchmark_sets()
    records: list[dict[str, Any]] = []
    execution_cache: dict[str, Any] = {}
    context_cache: dict[str, Any] = {}
    specs = build_specs(edition)
    for spec in specs:
        normalized_question = " ".join(spec.question.lower().split())
        normalized_sql = canonical_sql(spec.sql)
        if normalized_question in internal_questions or normalized_sql in internal_sql:
            raise ValueError(f"Vazamento para benchmark Pagila congelado: {spec.identifier}")
        if normalized_sql not in execution_cache:
            execution_cache[normalized_sql] = tools.execute_readonly_sql(normalized_sql, max_rows=10)
        execution = execution_cache[normalized_sql]
        if not execution.approved or execution.error:
            raise RuntimeError(f"Consulta não executável ({spec.identifier}): {execution.error or execution.reason}")
        if normalized_sql not in context_cache:
            schema_lookup = tools.get_enriched_table_schema if edition == "v3" else tools.get_table_schema
            context_cache[normalized_sql] = compile_schema_context(normalized_sql, schema_lookup)
        context = context_cache[normalized_sql]
        records.append(
            {
                "id": spec.identifier,
                "family": spec.family,
                "question": spec.question,
                "sql": normalized_sql,
                "relations": list(context.relations),
                "messages": _messages(context.ddl, spec.question, normalized_sql),
                "execution_validated": True,
            }
        )
    return records, {
        "internal_pagila_benchmark_questions": len(internal_questions),
        "internal_pagila_benchmark_sql": len(internal_sql),
        "specialization_fingerprint": corpus_fingerprint(specs),
        "unique_executable_sql": len(execution_cache),
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    digest = sha256()
    with path.open("x", encoding="utf-8", newline="\n") as file:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False, sort_keys=True)
            file.write(line + "\n")
            digest.update((line + "\n").encode("utf-8"))
    return digest.hexdigest()


def generate(*, output: Path, tools: PagilaAgentTools, edition: str = "v1") -> dict[str, Any]:
    if edition not in VALIDATION_FAMILIES_BY_EDITION:
        raise ValueError("edition deve ser v1, v2 ou v3.")
    if output.exists():
        raise FileExistsError(f"A saída já existe para preservar reprodutibilidade: {output}")
    records, guard = build_records(tools, edition=edition)
    validation_families = VALIDATION_FAMILIES_BY_EDITION[edition]
    train = [record for record in records if record["family"] not in validation_families]
    validation = [record for record in records if record["family"] in validation_families]
    if not train or not validation:
        raise RuntimeError("A divisão train/validation está vazia.")
    output.mkdir(parents=True)
    train_sha = _write_jsonl(output / "train.jsonl", train)
    validation_sha = _write_jsonl(output / "validation.jsonl", validation)
    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "validated",
        "edition": edition,
        "dialect": "postgres",
        "database": tools.database,
        "container": tools.container,
        "source": "pagila-v18-fc7a867-public",
        "generation": "parameterized-public-templates",
        "schema_context_version": "pagila-enriched-v1" if edition == "v3" else "pagila-columns-v1",
        "external_sakila_included": False,
        "frozen_internal_pagila_benchmark_included": False,
        "validation_families": sorted(validation_families),
        "train_examples": len(train),
        "validation_examples": len(validation),
        "families": sorted({record["family"] for record in records}),
        "train_sha256": train_sha,
        "validation_sha256": validation_sha,
        **guard,
    }
    with (output / "corpus-manifest.json").open("x", encoding="utf-8", newline="\n") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    return manifest


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="sqllm-pagila-postgres")
    parser.add_argument("--database", default="pagila")
    parser.add_argument("--label", default="pagila-v18-fc7a867-pt-v1")
    parser.add_argument("--edition", choices=("v1", "v2", "v3"), default="v1")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    result = generate(
        output=ROOT / "data" / "processed" / ("phase-03" if arguments.edition == "v3" else "phase-02") / arguments.label,
        tools=PagilaAgentTools(container=arguments.container, database=arguments.database),
        edition=arguments.edition,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

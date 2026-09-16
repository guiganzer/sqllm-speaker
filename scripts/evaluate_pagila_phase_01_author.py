"""Mede o autor SQL da fase 1 no benchmark público congelado do Pagila."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.context_compiler import ContextCompilationError, compile_relations_context, extract_relation_names, validate_relation_scope
from llm_to_sql.agentic.model_author import DEFAULT_MODEL_ID, DEFAULT_MODEL_REVISION, PhaseOneSqlAuthor
from llm_to_sql.agentic.pagila_tools import PagilaAgentTools
from llm_to_sql.evaluation import canonical_sql
from scripts.generate_pagila_evaluation import build_specs


DEFAULT_ADAPTER = ROOT / "artifacts" / "runs" / "phase-01-general-e1-768f209d9ea8"


def rows_hash(rows: tuple[tuple[str, ...], ...]) -> str:
    payload = "\n".join("\t".join(row) for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    if not total:
        raise ValueError("A avaliação precisa de ao menos um registro.")
    rates = {}
    for field in ("parse_and_scope_valid", "policy_allowed", "executed", "result_match", "canonical_exact_match"):
        count = sum(bool(record[field]) for record in records)
        rates[field] = {"count": count, "rate": count / total}
    by_category = {}
    for category in sorted({record["category"] for record in records}):
        subset = [record for record in records if record["category"] == category]
        by_category[category] = {
            "examples": len(subset),
            "executed_count": sum(bool(record["executed"]) for record in subset),
            "result_match_count": sum(bool(record["result_match"]) for record in subset),
        }
    return {"examples": total, "metrics": rates, "by_category": by_category}


def read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def benchmark_fingerprint() -> str:
    """Identifica imutavelmente perguntas e SQLs de referência do benchmark."""

    payload = [{"id": spec.identifier, "question": spec.question, "sql": spec.sql} for spec in build_specs()]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-path", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--model-revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--max-context-characters", type=int, default=6_000)
    parser.add_argument("--max-rows", type=int, default=1_000)
    parser.add_argument("--label", default="phase-01-pagila-author-baseline")
    parser.add_argument("--max-examples-per-run", type=int, default=4, help="Bloco retomável; 4 evita longas sessões de GPU.")
    parser.add_argument("--resume", action="store_true", help="Continua um diretório de artefato já existente.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.max_examples_per_run < 1:
        raise ValueError("max-examples-per-run deve ser positivo.")
    output = ROOT / "artifacts" / "evaluations" / arguments.label
    predictions_path = output / "predictions.jsonl"
    if output.exists() and not arguments.resume:
        raise FileExistsError(f"Saída já existe: {output}; use --resume para continuar.")
    output.mkdir(parents=True, exist_ok=True)
    records = read_records(predictions_path)
    completed = {record["id"] for record in records}
    specs = build_specs()
    pending = [spec for spec in specs if spec.identifier not in completed]
    selected = pending[: arguments.max_examples_per_run]
    if selected:
        tools = PagilaAgentTools()
        author = PhaseOneSqlAuthor(
            adapter_path=arguments.adapter_path,
            model_id=arguments.model_id,
            model_revision=arguments.model_revision,
            max_new_tokens=arguments.max_new_tokens,
        )
        with predictions_path.open("a", encoding="utf-8", newline="\n") as file:
            for spec in selected:
                relations = extract_relation_names(spec.sql)
                schemas = {relation: tools.get_table_schema(relation) for relation in relations}
                context = compile_relations_context(relations, schemas.__getitem__, max_characters=arguments.max_context_characters)
                reference = tools.execute_readonly_sql(spec.sql, max_rows=arguments.max_rows)
                if reference.error or not reference.approved:
                    raise RuntimeError(f"Referência Pagila inválida: {spec.identifier}: {reference.error or reference.reason}")
                candidate = author.generate(spec.question, context.ddl)
                record: dict[str, Any] = {
                    "id": spec.identifier,
                    "category": spec.category,
                    "question": spec.question,
                    "relations": relations,
                    "context_characters": context.characters,
                    "generated_sql": candidate,
                    "parse_and_scope_valid": False,
                    "policy_allowed": False,
                    "executed": False,
                    "result_match": False,
                    "canonical_exact_match": canonical_sql(candidate) == canonical_sql(spec.sql),
                    "reference_rows": len(reference.rows),
                    "reference_hash": rows_hash(reference.rows),
                    "error": None,
                }
                try:
                    validate_relation_scope(candidate, context.relations)
                    record["parse_and_scope_valid"] = True
                except ContextCompilationError as error:
                    record["error"] = f"schema_scope: {error}"
                if record["parse_and_scope_valid"]:
                    execution = tools.execute_readonly_sql(candidate, max_rows=arguments.max_rows)
                    record["policy_allowed"] = execution.approved
                    record["executed"] = execution.approved and execution.error is None and not execution.truncated
                    if execution.error:
                        record["error"] = execution.error
                    elif execution.approved:
                        record["generated_rows"] = len(execution.rows)
                        record["generated_hash"] = rows_hash(execution.rows)
                        record["result_match"] = not execution.truncated and execution.rows == reference.rows
                file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
                file.write("\n")
                file.flush()
                records.append(record)
                print(
                    f"[{len(records)}/{len(specs)}] {spec.identifier} "
                    f"scope={record['parse_and_scope_valid']} executed={record['executed']} result_match={record['result_match']}",
                    flush=True,
                )
    report = {
        "updated_at_utc": datetime.now(UTC).isoformat(),
        "complete": len(records) == len(specs),
        "evaluated_examples": len(records),
        "total_examples": len(specs),
        "benchmark_fingerprint_sha256": benchmark_fingerprint(),
        "label": arguments.label,
        "model_id": arguments.model_id,
        "model_revision": arguments.model_revision,
        "adapter_path": str(arguments.adapter_path),
        "max_new_tokens": arguments.max_new_tokens,
        "max_context_characters": arguments.max_context_characters,
        "schema_selection": "Relações extraídas da SQL de referência apenas para isolar e medir o autor SQL; não mede o especialista de schema.",
        "comparison_contract": "Repetir com a mesma lista pública, parâmetros e relações candidatas após a especialização Pagila.",
        "summary": aggregate(records) if records else None,
    }
    with (output / "report.json").open("w", encoding="utf-8", newline="\n") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
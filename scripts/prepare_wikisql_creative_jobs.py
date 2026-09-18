"""Cria planos semânticos e prompts de redação PT-BR para WikiSQL."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.wikisql import execute_reference, parse_query, parse_table, render_schema, render_sql


AGGREGATIONS = ("none", "MAX", "MIN", "COUNT", "SUM", "AVG")
OPERATORS = ("=", ">", "<")
SPLITS = ("train", "validation", "test")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data" / "raw" / "kaggle__thedevastator__wikisql")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "interim" / "wikisql-creative-v1" / "writer-jobs")
    parser.add_argument("--splits", nargs="+", choices=SPLITS, default=list(SPLITS))
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--limit-per-split", type=int, help="Primeiros N; use apenas em smoke.")
    selection.add_argument("--sample-size-per-split", type=int, help="Amostra determinística por hash.")
    selection.add_argument("--sample-plan", help="Ex.: train=6000,validation=1000,test=1000.")
    parser.add_argument("--skip-execution", action="store_true")
    return parser.parse_args()


def _writer_messages(config: dict[str, object], job: dict[str, object]) -> list[dict[str, str]]:
    expected = {
        "candidates": [
            {"id": "c1", "style": "direta", "question": "... ?"},
            {"id": "c2", "style": "analitica", "question": "... ?"},
            {"id": "c3", "style": "conversacional", "question": "... ?"},
            {"id": "c4", "style": "concisa", "question": "... ?"},
        ]
    }
    user = (
        "PLANO_SEMANTICO:\n" + json.dumps(job["semantic_brief"], ensure_ascii=False, indent=2) +
        "\n\nSCHEMA:\n" + str(job["schema"]) +
        "\n\nSQL_REFERENCIA:\n" + str(job["reference_sql"]) +
        "\n\nPERGUNTA_ORIGINAL_EN:\n" + str(job["source_question_en"]) +
        "\n\nFORMATO_DE_SAIDA:\n" + json.dumps(expected, ensure_ascii=False)
    )
    return [{"role": "system", "content": str(config["system"])}, {"role": "user", "content": user}]


def prepare_split(
    source: Path,
    destination: Path,
    split: str,
    limit: int | None,
    sample_size: int | None,
    execute: bool,
    config: dict[str, object],
) -> dict[str, object]:
    if destination.exists():
        raise FileExistsError(f"Saída já existe: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(2**31 - 1)
    if sample_size is not None and sample_size < 1:
        raise ValueError("sample_size deve ser positivo.")
    selected_indices: set[int] | None = None
    if sample_size is not None:
        with source.open(encoding="utf-8-sig", newline="") as count_handle:
            row_count = sum(1 for _ in csv.DictReader(count_handle))
        ranked = sorted(
            range(row_count),
            key=lambda index: hashlib.sha256(f"{split}:{index}".encode("utf-8")).digest(),
        )
        selected_indices = set(ranked[: min(sample_size, row_count)])
    accepted = 0
    digest = hashlib.sha256()
    with source.open(encoding="utf-8-sig", newline="") as input_handle, destination.open("x", encoding="utf-8", newline="\n") as output_handle:
        for index, row in enumerate(csv.DictReader(input_handle)):
            if limit is not None and index >= limit:
                break
            if selected_indices is not None and index not in selected_indices:
                continue
            table = parse_table(row["table"])
            query = parse_query(row["sql"], column_count=len(table.headers))
            reference_sql = render_sql(table, query)
            result = execute_reference(table, reference_sql) if execute else ()
            semantic_brief = {
                "result_column": table.headers[query.selected_column],
                "aggregation": AGGREGATIONS[query.aggregation],
                "conditions": [
                    {"column": table.headers[column], "operator": OPERATORS[operator], "value": value}
                    for column, operator, value in zip(query.condition_columns, query.condition_operators, query.condition_values)
                ],
                "connector": "AND",
                "literal_values": list(query.condition_values),
                "answer_shape": "scalar" if query.aggregation else "list",
                "reference_row_count": len(result) if execute else None,
            }
            job: dict[str, object] = {
                "id": f"wikisql:{split}:{index}",
                "source_split": split,
                "source_question_en": row["question"].strip(),
                "table_id": table.identifier,
                "schema": render_schema(table),
                "reference_sql": reference_sql,
                "semantic_brief": semantic_brief,
                "prompt_id": config["id"],
            }
            job["messages"] = _writer_messages(config, job)
            line = json.dumps(job, ensure_ascii=False, separators=(",", ":"))
            output_handle.write(line + "\n")
            digest.update((line + "\n").encode("utf-8"))
            accepted += 1
    return {
        "split": split,
        "jobs": accepted,
        "sha256": digest.hexdigest(),
        "executed": execute,
        "selection": "first_n_smoke" if limit is not None else "deterministic_hash_sample" if sample_size is not None else "all",
    }


def main() -> None:
    arguments = parse_arguments()
    config = json.loads((ROOT / "configs" / "prompts" / "wikisql-question-writer-v1.json").read_text(encoding="utf-8"))
    sample_plan: dict[str, int] = {}
    if arguments.sample_plan:
        for item in arguments.sample_plan.split(","):
            name, separator, raw_value = item.partition("=")
            if not separator or name not in SPLITS or not raw_value.isdigit() or int(raw_value) < 1:
                raise SystemExit(f"Item inválido em --sample-plan: {item}")
            sample_plan[name] = int(raw_value)
    summaries = []
    for split in arguments.splits:
        summaries.append(
            prepare_split(
                arguments.input_dir / f"{split}.csv",
                arguments.output_dir / f"{split}.jsonl",
                split,
                arguments.limit_per_split,
                sample_plan.get(split, arguments.sample_size_per_split),
                not arguments.skip_execution,
                config,
            )
        )
    manifest = {"id": "wikisql-creative-writer-jobs-v1", "prompt_id": config["id"], "splits": summaries}
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    (arguments.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

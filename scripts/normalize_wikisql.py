"""Normaliza a exportação Kaggle do WikiSQL sem executar repr arbitrário."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

from sqlglot import parse_one

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.policy import ReadOnlySqlPolicy
from llm_to_sql.wikisql import execute_reference, parse_query, parse_table, render_schema, render_sql


SPLITS = ("train", "validation", "test")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "data" / "raw" / "kaggle__thedevastator__wikisql",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "processed" / "wikisql-normalized-v1",
    )
    parser.add_argument("--limit-per-split", type=int)
    parser.add_argument("--skip-execution", action="store_true")
    return parser.parse_args()


def normalize_split(
    *,
    source: Path,
    destination: Path,
    split: str,
    limit: int | None,
    execute: bool,
) -> dict[str, object]:
    if limit is not None and limit < 1:
        raise ValueError("limit deve ser positivo.")
    policy = ReadOnlySqlPolicy()
    accepted = 0
    rejected = 0
    digest = hashlib.sha256()
    rejection_reasons: dict[str, int] = {}
    destination.parent.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(2**31 - 1)
    with source.open(encoding="utf-8-sig", newline="") as input_handle, destination.open(
        "w", encoding="utf-8", newline="\n"
    ) as output_handle:
        for index, row in enumerate(csv.DictReader(input_handle)):
            if limit is not None and index >= limit:
                break
            try:
                table = parse_table(row["table"])
                query = parse_query(row["sql"], column_count=len(table.headers))
                sql = render_sql(table, query)
                decision = policy.validate(sql)
                if not decision.allowed:
                    raise ValueError(decision.reason)
                parse_one(sql, read="sqlite")
                result_rows = execute_reference(table, sql) if execute else ()
                record = {
                    "id": f"wikisql:{split}:{index}",
                    "source": "kaggle__thedevastator__wikisql",
                    "source_split": split,
                    "language": "en",
                    "training_ready": False,
                    "training_blocker": "requires_pt_br_translation_and_semantic_review",
                    "dialect": "sqlite",
                    "question": row["question"].strip(),
                    "table_id": table.identifier,
                    "schema": render_schema(table),
                    "sql": sql,
                    "reference_row_count": len(result_rows) if execute else None,
                }
                line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                output_handle.write(line + "\n")
                digest.update((line + "\n").encode("utf-8"))
                accepted += 1
            except Exception as error:  # rejeições são contabilizadas no manifesto
                rejected += 1
                reason = f"{type(error).__name__}: {str(error)[:160]}"
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    return {
        "split": split,
        "source": source.as_posix(),
        "output": destination.as_posix(),
        "accepted": accepted,
        "rejected": rejected,
        "executed": execute,
        "sha256": digest.hexdigest(),
        "rejection_reasons": rejection_reasons,
    }


def main() -> None:
    arguments = parse_arguments()
    summaries = []
    for split in SPLITS:
        summaries.append(
            normalize_split(
                source=arguments.input_dir / f"{split}.csv",
                destination=arguments.output_dir / f"{split}.jsonl",
                split=split,
                limit=arguments.limit_per_split,
                execute=not arguments.skip_execution,
            )
        )
    manifest = {
        "id": "wikisql-normalized-v1",
        "source_splits_preserved": True,
        "safe_parser": "restricted_ast_no_eval",
        "training_ready": False,
        "training_blocker": "requires_pt_br_translation_and_semantic_review",
        "splits": summaries,
    }
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = arguments.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

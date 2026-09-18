"""Compara a SQL retornada por candidato com a referência por estrutura e execução."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.evaluation import assess_sql, canonical_sql, normalize_model_output
from llm_to_sql.wikisql import execute_reference, parse_table


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roundtrip-jobs", type=Path, required=True)
    parser.add_argument("--roundtrip-responses", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw" / "kaggle__thedevastator__wikisql")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _read(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_tables(raw_dir: Path, requested: dict[str, set[int]]) -> dict[tuple[str, int], object]:
    csv.field_size_limit(2**31 - 1)
    tables: dict[tuple[str, int], object] = {}
    for split, indexes in requested.items():
        if not indexes:
            continue
        loaded = 0
        with (raw_dir / f"{split}.csv").open(encoding="utf-8-sig", newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle)):
                if index in indexes:
                    tables[(split, index)] = parse_table(row["table"])
                    loaded += 1
                if loaded == len(indexes):
                    break
    return tables


def _row_counter(rows: tuple[tuple[object, ...], ...]) -> Counter[str]:
    return Counter(json.dumps(list(row), ensure_ascii=False, default=str, sort_keys=True) for row in rows)


def main() -> None:
    arguments = parse_arguments()
    if arguments.output.exists():
        raise SystemExit(f"Saída já existe: {arguments.output}")
    jobs = {str(record["id"]): record for record in _read(arguments.roundtrip_jobs)}
    responses = {str(record["id"]): record for record in _read(arguments.roundtrip_responses)}
    requested: dict[str, set[int]] = {}
    for job in jobs.values():
        requested.setdefault(str(job["source_split"]), set()).add(int(job["source_index"]))
    tables = _load_tables(arguments.raw_dir, requested)
    output = []
    for identifier, job in jobs.items():
        response = responses.get(identifier)
        if response is None:
            continue
        candidate_sql = normalize_model_output(str(response["response"]))
        reference_sql = str(job["reference_sql"])
        assessment = assess_sql(candidate_sql, str(job["schema"]))
        exact = canonical_sql(candidate_sql) == canonical_sql(reference_sql)
        executed = False
        result_equivalent = False
        execution_error = None
        reference_rows: tuple[tuple[object, ...], ...] = ()
        if assessment.policy_allowed and assessment.schema_references_valid:
            table = tables[(str(job["source_split"]), int(job["source_index"]))]
            try:
                reference_rows = execute_reference(table, reference_sql)
                candidate_rows = execute_reference(table, candidate_sql)
                executed = True
                result_equivalent = _row_counter(reference_rows) == _row_counter(candidate_rows)
            except Exception as error:
                execution_error = f"{type(error).__name__}: {str(error)[:300]}"
        approved = assessment.policy_allowed and assessment.schema_references_valid and (
            exact or (executed and bool(reference_rows) and result_equivalent)
        )
        output.append(
            {
                "id": identifier,
                "writer_job_id": job["writer_job_id"],
                "candidate_id": job["candidate_id"],
                "question": job["question"],
                "approved": approved,
                "exact_match": exact,
                "executed": executed,
                "result_equivalent": result_equivalent,
                "reference_row_count": len(reference_rows),
                "schema_references_valid": assessment.schema_references_valid,
                "policy_allowed": assessment.policy_allowed,
                "candidate_sql": candidate_sql,
                "execution_error": execution_error,
            }
        )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8", newline="\n") as handle:
        for record in output:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"evaluated": len(output), "approved": sum(bool(row["approved"]) for row in output)}, indent=2))


if __name__ == "__main__":
    main()

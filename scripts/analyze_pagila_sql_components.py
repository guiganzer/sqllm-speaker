"""Produz métricas estruturais para um predictions.jsonl do benchmark Pagila."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.evaluation_components import aggregate_component_matches, compare_sql_components
from scripts.generate_pagila_evaluation import build_specs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    references = {spec.identifier: spec.sql for spec in build_specs()}
    records = []
    with arguments.predictions.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            prediction = json.loads(line)
            identifier = prediction["id"]
            if identifier not in references:
                raise KeyError(f"ID fora do benchmark congelado: {identifier}")
            matches = compare_sql_components(references[identifier], prediction["generated_sql"])
            records.append({"id": identifier, "matches": matches})
    report = {
        "examples": len(records),
        "metrics": aggregate_component_matches(row["matches"] for row in records),
        "records": records,
    }
    output = arguments.output or arguments.predictions.with_name("component-report.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

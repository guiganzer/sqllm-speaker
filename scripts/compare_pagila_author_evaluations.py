"""Compara dois relatórios completos do benchmark público Pagila."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


METRICS = ("parse_and_scope_valid", "policy_allowed", "executed", "result_match", "canonical_exact_match")


def read_complete_report(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        report = json.load(file)
    if not report.get("complete"):
        raise ValueError(f"Relatório incompleto: {path}")
    return report


def compare_reports(baseline: dict, candidate: dict) -> dict:
    required = ("benchmark_fingerprint_sha256", "total_examples", "max_new_tokens", "max_context_characters")
    for field in required:
        if baseline.get(field) != candidate.get(field):
            raise ValueError(f"Contratos incompatíveis em {field}.")
    rows = []
    for metric in METRICS:
        before = baseline["summary"]["metrics"][metric]
        after = candidate["summary"]["metrics"][metric]
        rows.append(
            {
                "metric": metric,
                "baseline_count": before["count"],
                "candidate_count": after["count"],
                "delta_count": after["count"] - before["count"],
                "baseline_rate": before["rate"],
                "candidate_rate": after["rate"],
                "delta_rate": after["rate"] - before["rate"],
            }
        )
    return {
        "benchmark_fingerprint_sha256": baseline["benchmark_fingerprint_sha256"],
        "examples": baseline["total_examples"],
        "baseline_label": baseline["label"],
        "candidate_label": candidate["label"],
        "metrics": rows,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="report.json pré-especialização.")
    parser.add_argument("--candidate", type=Path, required=True, help="report.json pós-especialização.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    print(json.dumps(compare_reports(read_complete_report(arguments.baseline), read_complete_report(arguments.candidate)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
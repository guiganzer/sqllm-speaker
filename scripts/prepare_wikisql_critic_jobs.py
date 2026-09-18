"""Cria jobs do crítico usando somente candidatos aprovados no retorno para SQL."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--writer-jobs", type=Path, required=True)
    parser.add_argument("--roundtrip-evaluations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _read(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    arguments = parse_arguments()
    if arguments.output.exists():
        raise SystemExit(f"Saída já existe: {arguments.output}")
    writer_jobs = {str(record["id"]): record for record in _read(arguments.writer_jobs)}
    approved: dict[str, list[dict[str, object]]] = defaultdict(list)
    for evaluation in _read(arguments.roundtrip_evaluations):
        if evaluation["approved"]:
            approved[str(evaluation["writer_job_id"])].append(
                {
                    "id": evaluation["candidate_id"],
                    "question": evaluation["question"],
                    "exact_match": evaluation["exact_match"],
                    "result_equivalent": evaluation["result_equivalent"],
                }
            )
    config = json.loads((ROOT / "configs" / "prompts" / "wikisql-question-critic-v1.json").read_text(encoding="utf-8"))
    jobs = []
    for identifier, candidates in approved.items():
        source = writer_jobs[identifier]
        user = (
            "PLANO_SEMANTICO:\n" + json.dumps(source["semantic_brief"], ensure_ascii=False, indent=2)
            + "\n\nPERGUNTA_ORIGINAL_EN:\n" + str(source["source_question_en"])
            + "\n\nCANDIDATOS_APROVADOS:\n" + json.dumps(candidates, ensure_ascii=False, indent=2)
        )
        jobs.append(
            {
                "id": identifier,
                "source_split": source["source_split"],
                "schema": source["schema"],
                "reference_sql": source["reference_sql"],
                "semantic_brief": source["semantic_brief"],
                "approved_candidates": candidates,
                "messages": [
                    {"role": "system", "content": config["system"]},
                    {"role": "user", "content": user},
                ],
            }
        )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8", newline="\n") as handle:
        for record in jobs:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"writer_jobs": len(writer_jobs), "critic_jobs": len(jobs), "needs_repair": len(writer_jobs) - len(jobs)}, indent=2))


if __name__ == "__main__":
    main()

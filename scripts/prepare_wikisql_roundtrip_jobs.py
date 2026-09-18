"""Valida candidatos PT-BR e cria jobs de retorno pergunta-para-SQL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.model_author import AUTHOR_PROMPT_ID, build_author_messages
from llm_to_sql.creative_questions import validate_writer_candidates


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--writer-jobs", type=Path, required=True)
    parser.add_argument("--writer-responses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _read(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    arguments = parse_arguments()
    if arguments.output.exists():
        raise SystemExit(f"Saída já existe: {arguments.output}")
    jobs = {str(record["id"]): record for record in _read(arguments.writer_jobs)}
    responses = {str(record["id"]): record for record in _read(arguments.writer_responses)}
    output: list[dict[str, object]] = []
    rejections: list[dict[str, object]] = []
    for identifier, job in jobs.items():
        response = responses.get(identifier)
        if response is None:
            continue
        try:
            candidates, candidate_rejections = validate_writer_candidates(
                str(response["response"]), dict(job["semantic_brief"])
            )
        except ValueError as error:
            rejections.append({"id": identifier, "stage": "writer_contract", "error": str(error)})
            continue
        for rejection in candidate_rejections:
            rejections.append(
                {
                    "id": identifier,
                    "candidate_id": rejection.identifier,
                    "style": rejection.style,
                    "stage": "writer_candidate_contract",
                    "error": rejection.error,
                }
            )
        if len(candidates) < 2:
            rejections.append(
                {
                    "id": identifier,
                    "stage": "writer_contract",
                    "error": "Menos de dois candidatos válidos para comparação crítica.",
                }
            )
            continue
        for candidate in candidates:
            candidate_id = f"{identifier}:{candidate.identifier}"
            output.append(
                {
                    "id": candidate_id,
                    "writer_job_id": identifier,
                    "candidate_id": candidate.identifier,
                    "style": candidate.style,
                    "question": candidate.question,
                    "source_split": job["source_split"],
                    "source_index": int(identifier.rsplit(":", 1)[1]),
                    "schema": job["schema"],
                    "reference_sql": job["reference_sql"],
                    "semantic_brief": job["semantic_brief"],
                    "prompt_id": AUTHOR_PROMPT_ID,
                    "messages": build_author_messages(candidate.question, str(job["schema"])),
                }
            )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("x", encoding="utf-8", newline="\n") as handle:
        for record in output:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    rejection_path = arguments.output.with_name(arguments.output.stem + ".rejections.jsonl")
    with rejection_path.open("x", encoding="utf-8", newline="\n") as handle:
        for record in rejections:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "writer_jobs": len(jobs),
                "writer_responses": len(responses),
                "roundtrip_jobs": len(output),
                "writer_rejections": len({record["id"] for record in rejections if record["stage"] == "writer_contract"}),
                "candidate_rejections": sum(record["stage"] == "writer_candidate_contract" for record in rejections),
                "missing_responses": len(set(jobs) - set(responses)),
                "rejections": str(rejection_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

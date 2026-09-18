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

from llm_to_sql.creative_questions import validate_writer_response


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
    sql_prompt = json.loads((ROOT / "configs" / "prompts" / "sql-author-schema-fk-v1.json").read_text(encoding="utf-8"))
    output: list[dict[str, object]] = []
    rejections: list[dict[str, object]] = []
    for identifier, job in jobs.items():
        response = responses.get(identifier)
        if response is None:
            continue
        try:
            candidates = validate_writer_response(str(response["response"]), dict(job["semantic_brief"]))
        except ValueError as error:
            rejections.append({"id": identifier, "stage": "writer_contract", "error": str(error)})
            continue
        for candidate in candidates:
            candidate_id = f"{identifier}:{candidate.identifier}"
            user = (
                "<dialeto>\nsqlite\n</dialeto>\n\n<schema_e_relacionamentos>\n"
                + str(job["schema"])
                + "\n</schema_e_relacionamentos>\n\n<pergunta>\n"
                + candidate.question
                + "\n</pergunta>\n\nRetorne somente uma consulta SQL de leitura."
            )
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
                    "messages": [
                        {"role": "system", "content": sql_prompt["system"]},
                        {"role": "user", "content": user},
                    ],
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
                "writer_rejections": len(rejections),
                "missing_responses": len(set(jobs) - set(responses)),
                "rejections": str(rejection_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

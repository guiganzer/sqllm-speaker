"""Finaliza perguntas escolhidas pelo crítico em corpus Text-to-SQL treinável."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.creative_questions import validate_critic_response


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--critic-jobs", type=Path, required=True)
    parser.add_argument("--critic-responses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _read(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    arguments = parse_arguments()
    if arguments.output.exists():
        raise SystemExit(f"Saída já existe: {arguments.output}")
    jobs = {str(record["id"]): record for record in _read(arguments.critic_jobs)}
    responses = {str(record["id"]): record for record in _read(arguments.critic_responses)}
    system = json.loads((ROOT / "configs" / "prompts" / "sql-author-schema-fk-v1.json").read_text(encoding="utf-8"))["system"]
    records = []
    for identifier, job in jobs.items():
        response = responses.get(identifier)
        if response is None:
            continue
        candidates = {str(item["id"]): item for item in job["approved_candidates"]}
        critic = validate_critic_response(str(response["response"]), set(candidates))
        selected = candidates[str(critic["selected_id"])]
        question = str(selected["question"])
        user = f"<schema>\n{job['schema']}\n</schema>\n<pergunta>\n{question}\n</pergunta>"
        records.append(
            {
                "id": identifier,
                "source": "wikisql-creative-pt-v1",
                "source_split": job["source_split"],
                "language": "pt-BR",
                "dialect": "sqlite",
                "question": question,
                "sql": job["reference_sql"],
                "schema": job["schema"],
                "semantic_brief": job["semantic_brief"],
                "critic": critic,
                "roundtrip_validated": True,
                "training_ready": True,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": job["reference_sql"]},
                ],
            }
        )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with arguments.output.open("x", encoding="utf-8", newline="\n") as handle:
        for record in records:
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
            handle.write(line + "\n")
            digest.update((line + "\n").encode("utf-8"))
    print(json.dumps({"jobs": len(jobs), "finalized": len(records), "sha256": digest.hexdigest()}, indent=2))


if __name__ == "__main__":
    main()

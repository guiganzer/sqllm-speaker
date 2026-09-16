"""Executa a sessão Pagila com o adapter da fase 1 como autor SQL local."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.context_compiler import ContextCompilationError, compile_relations_context, validate_relation_scope
from llm_to_sql.agentic.model_author import (
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    PhaseOneSqlAuthor,
)
from llm_to_sql.agentic.pagila_tools import PagilaAgentTools
from llm_to_sql.agentic.workflow import AgenticWorkflow, SessionStage


DEFAULT_ADAPTER = ROOT / "artifacts" / "runs" / "phase-01-general-e1-768f209d9ea8"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True, help="Pergunta em português.")
    parser.add_argument(
        "--tables",
        required=True,
        help="Relações candidatas separadas por vírgula, selecionadas pelo especialista de schema.",
    )
    parser.add_argument("--adapter-path", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--model-revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--max-context-characters", type=int, default=6_000)
    parser.add_argument("--max-rows", type=int, default=100)
    return parser.parse_args()


def selected_relations(value: str) -> tuple[str, ...]:
    relations = tuple(item.strip() for item in value.split(",") if item.strip())
    if not relations:
        raise ValueError("--tables deve conter ao menos uma relação.")
    return relations


def result_payload(session, profile, context, candidates: list[str], execution=None) -> dict:
    payload = {
        "stage": session.stage,
        "reason": session.final_reason,
        "profile": profile,
        "tables_loaded": sorted(session.table_schemas),
        "context_characters": context.characters,
        "context_relations": context.relations,
        "generated_candidates": candidates,
        "sql": session.sql,
        "repairs": session.repairs,
    }
    if execution is not None:
        payload.update(
            {
                "rows": execution.rows,
                "truncated": execution.truncated,
                "error": execution.error,
            }
        )
    return payload


def main() -> None:
    arguments = parse_arguments()
    relations = selected_relations(arguments.tables)
    tools = PagilaAgentTools()
    workflow = AgenticWorkflow(max_repairs=1)
    session = workflow.begin(arguments.question)
    profile = tools.get_database_profile()
    schemas = {relation: tools.get_table_schema(relation) for relation in relations}
    context = compile_relations_context(relations, schemas.__getitem__, max_characters=arguments.max_context_characters)
    workflow.add_schemas(session, schemas)
    author = PhaseOneSqlAuthor(
        adapter_path=arguments.adapter_path,
        model_id=arguments.model_id,
        model_revision=arguments.model_revision,
        max_new_tokens=arguments.max_new_tokens,
    )
    candidates: list[str] = []
    while session.stage is SessionStage.AWAITING_SQL:
        candidate = author.generate(session.question, context.ddl, session.final_reason if session.repairs else None)
        candidates.append(candidate)
        try:
            validate_relation_scope(candidate, context.relations)
        except ContextCompilationError as error:
            workflow.finalize_without_execution(session, f"Guardião de schema: {error}")
            print(json.dumps(result_payload(session, profile, context, candidates), ensure_ascii=False, indent=2, default=str))
            return
        policy = workflow.submit_sql(session, candidate)
        if not policy.allowed:
            print(json.dumps(result_payload(session, profile, context, candidates), ensure_ascii=False, indent=2, default=str))
            return
        execution = tools.execute_readonly_sql(policy.normalized_sql or "", max_rows=arguments.max_rows)
        workflow.record_execution(session, succeeded=execution.error is None, sanitized_error=execution.error)
        if session.stage is SessionStage.FINALIZED or session.stage is SessionStage.BLOCKED:
            print(
                json.dumps(
                    result_payload(session, profile, context, candidates, execution),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
            return
        workflow.add_schemas(session, schemas)
    raise RuntimeError(f"Estado inesperado da sessão: {session.stage}")


if __name__ == "__main__":
    main()
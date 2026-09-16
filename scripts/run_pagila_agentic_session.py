"""Executa uma sessão agentic real contra o Pagila local com SQL fornecido pelo autor/modelo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.pagila_tools import PagilaAgentTools
from llm_to_sql.agentic.workflow import AgenticWorkflow


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--tables", required=True, help="Lista de tabelas/views separadas por vírgula, obtidas pelo especialista de schema.")
    parser.add_argument("--sql", required=True, help="SQL proposto pelo autor SQL.")
    parser.add_argument("--max-rows", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    tools = PagilaAgentTools()
    workflow = AgenticWorkflow(max_repairs=1)
    session = workflow.begin(arguments.question)
    profile = tools.get_database_profile()
    selected_tables = [item.strip() for item in arguments.tables.split(",") if item.strip()]
    workflow.add_schemas(session, {table_name: tools.get_table_schema(table_name) for table_name in selected_tables})
    policy = workflow.submit_sql(session, arguments.sql)
    if not policy.allowed:
        print(json.dumps({"stage": session.stage, "reason": session.final_reason, "profile": profile}, ensure_ascii=False, indent=2))
        return
    execution = tools.execute_readonly_sql(policy.normalized_sql or "", max_rows=arguments.max_rows)
    workflow.record_execution(session, succeeded=execution.error is None, sanitized_error=execution.error)
    print(
        json.dumps(
            {
                "stage": session.stage,
                "reason": session.final_reason,
                "profile": profile,
                "tables_loaded": sorted(session.table_schemas),
                "sql": execution.sql,
                "rows": execution.rows,
                "truncated": execution.truncated,
                "error": execution.error,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()

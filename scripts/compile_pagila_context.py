"""Compila o contexto mínimo de schema Pagila para uma consulta de leitura."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.context_compiler import compile_schema_context
from llm_to_sql.agentic.pagila_tools import PagilaAgentTools


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sql", required=True)
    parser.add_argument("--max-characters", type=int, default=6_000)
    parser.add_argument("--show-ddl", action="store_true")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    tools = PagilaAgentTools()
    context = compile_schema_context(arguments.sql, tools.get_table_schema, max_characters=arguments.max_characters)
    result = {"relations": context.relations, "characters": context.characters}
    if arguments.show_ddl:
        result["ddl"] = context.ddl
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

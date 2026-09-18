"""Monta o prompt schema/FK e valida uma SQL no banco local correspondente."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.prompt_specializer import PromptTemplate, build_schema_fk_messages
from llm_to_sql.agentic.sqlite_validator import SqliteCatalogValidator
from llm_to_sql.schema_catalog import SchemaCatalog


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--pack", required=True)
    parser.add_argument("--question")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--sql")
    source.add_argument("--sql-file", type=Path)
    parser.add_argument(
        "--prompt-template",
        type=Path,
        default=ROOT / "configs" / "prompts" / "sql-author-schema-fk-v1.json",
    )
    parser.add_argument("--database", type=Path)
    parser.add_argument("--max-rows", type=int, default=100)
    parser.add_argument("--max-vm-steps", type=int, default=50_000_000)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    catalog = SchemaCatalog.load(arguments.catalog)
    payload: dict[str, object] = {
        "catalog": catalog.name,
        "dialect": catalog.dialect,
        "source_role": catalog.source.get("role"),
        "pack": arguments.pack,
        "tier": catalog.pack(arguments.pack).tier,
        "tables": catalog.pack(arguments.pack).tables,
        "schema_context": catalog.render_pack(arguments.pack),
    }
    if arguments.question:
        template = PromptTemplate.load(arguments.prompt_template)
        payload["prompt_id"] = template.identifier
        payload["messages"] = build_schema_fk_messages(
            question=arguments.question,
            catalog=catalog,
            pack_name=arguments.pack,
            template=template,
        )
    sql = arguments.sql
    if arguments.sql_file:
        sql = arguments.sql_file.read_text(encoding="utf-8")
    if sql is not None:
        database = arguments.database or (ROOT / (catalog.database_path or ""))
        validator = SqliteCatalogValidator(
            catalog=catalog,
            database_path=database,
            max_virtual_machine_steps=arguments.max_vm_steps,
        )
        payload["validation"] = validator.validate_and_execute(
            sql,
            pack_name=arguments.pack,
            max_rows=arguments.max_rows,
        ).as_dict()
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()

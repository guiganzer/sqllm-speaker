"""Valida e prepara o conjunto privado da fase 2, sem versionar seu conteúdo."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.private_data import prepare_private_dataset


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, required=True, help="JSONL privado com pergunta e SQL validado.")
    parser.add_argument("--base-schema", type=Path, required=True, help="DDL base privado do banco.")
    parser.add_argument("--endpoint-manifest", type=Path, help="JSONL opcional de snapshots raw_*/vw_ep_* por endpoint.")
    parser.add_argument("--dialect", default="postgres", help="Dialeto aceito pelo SQLGlot; padrão: postgres.")
    parser.add_argument("--validation-percent", type=int, default=10)
    parser.add_argument("--test-percent", type=int, default=10)
    parser.add_argument("--max-characters", type=int, default=16_000)
    parser.add_argument("--max-schema-characters", type=int, default=6_000)
    parser.add_argument("--output-label", required=True, help="Rótulo não sensível para a saída local.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    report = prepare_private_dataset(
        root_dir=ROOT,
        queries_path=arguments.queries.resolve(),
        base_schema_path=arguments.base_schema.resolve(),
        endpoint_manifest_path=arguments.endpoint_manifest.resolve() if arguments.endpoint_manifest else None,
        dialect=arguments.dialect,
        validation_percent=arguments.validation_percent,
        test_percent=arguments.test_percent,
        max_characters=arguments.max_characters,
        max_schema_characters=arguments.max_schema_characters,
        output_label=arguments.output_label,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

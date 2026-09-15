"""Verifica os invariantes dos JSONL produzidos na fase 1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def groups_in(path: Path) -> set[str]:
    groups: set[str] = set()
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                groups.add(json.loads(line)["schema_group"])
    return groups


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("processed_dir", type=Path)
    arguments = parser.parse_args()
    train = groups_in(arguments.processed_dir / "train.jsonl")
    validation = groups_in(arguments.processed_dir / "validation.jsonl")
    overlap = train & validation
    summary = {
        "train_schema_groups": len(train),
        "validation_schema_groups": len(validation),
        "overlapping_schema_groups": len(overlap),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if overlap:
        raise SystemExit("Falha: há schemas em ambos os splits.")


if __name__ == "__main__":
    main()

"""Prompt versionado e orientado a chaves para autoria Text-to-SQL."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from llm_to_sql.schema_catalog import SchemaCatalog


@dataclass(frozen=True)
class PromptTemplate:
    identifier: str
    system: str
    user_template: str

    @classmethod
    def load(cls, path: Path) -> "PromptTemplate":
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls(payload["id"], payload["system"], payload["user_template"])


def build_schema_fk_messages(
    *,
    question: str,
    catalog: SchemaCatalog,
    pack_name: str,
    template: PromptTemplate,
) -> list[dict[str, str]]:
    if not question.strip():
        raise ValueError("A pergunta não pode estar vazia.")
    schema = catalog.render_pack(pack_name)
    user = template.user_template.format(
        dialect=catalog.dialect,
        schema=schema,
        question=question.strip(),
    )
    return [
        {"role": "system", "content": template.system},
        {"role": "user", "content": user},
    ]

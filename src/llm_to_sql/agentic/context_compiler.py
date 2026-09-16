"""Compilação de contexto compacto de schema para consultas PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class SchemaContext:
    relations: tuple[str, ...]
    ddl: str
    characters: int


class ContextCompilationError(ValueError):
    """Indica SQL sem relações conhecidas ou contexto acima do orçamento."""


def extract_relation_names(sql: str) -> tuple[str, ...]:
    try:
        query = parse_one(sql, read="postgres")
    except ParseError as error:
        raise ContextCompilationError("SQL não fez parse como PostgreSQL.") from error
    cte_aliases = {cte.alias_or_name.lower() for cte in query.find_all(exp.CTE) if cte.alias_or_name}
    relations: list[str] = []
    seen: set[str] = set()
    for table in query.find_all(exp.Table):
        name = table.name.lower()
        if name in cte_aliases or not _IDENTIFIER.fullmatch(name) or name in seen:
            continue
        seen.add(name)
        relations.append(name)
    if not relations:
        raise ContextCompilationError("A consulta não referencia tabelas ou views públicas conhecidas.")
    return tuple(relations)


def compile_schema_context(
    sql: str,
    schema_lookup: Callable[[str], str],
    *,
    max_characters: int = 6_000,
) -> SchemaContext:
    if max_characters < 256:
        raise ValueError("max_characters deve ser no mínimo 256.")
    relations = extract_relation_names(sql)
    fragments = []
    for relation in relations:
        ddl = schema_lookup(relation).strip()
        if not ddl:
            raise ContextCompilationError(f"Schema vazio para relação {relation!r}.")
        fragments.append(ddl)
    compiled = "\n\n".join(fragments)
    if len(compiled) > max_characters:
        raise ContextCompilationError(
            f"Contexto de {len(compiled)} caracteres excede o orçamento de {max_characters}; reduza relações ou aumente o limite conscientemente."
        )
    return SchemaContext(relations, compiled, len(compiled))

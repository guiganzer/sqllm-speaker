"""Compilação de contexto compacto de schema para consultas PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Sequence

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


def validate_relation_scope(sql: str, allowed_relations: Sequence[str]) -> tuple[str, ...]:
    """Garante que a proposta usa somente relações presentes no contexto entregue."""

    allowed = {relation.lower().strip() for relation in allowed_relations}
    if not allowed or any(not _IDENTIFIER.fullmatch(relation) for relation in allowed):
        raise ValueError("allowed_relations deve conter relações públicas válidas.")
    referenced = extract_relation_names(sql)
    outside_scope = sorted(set(referenced) - allowed)
    if outside_scope:
        raise ContextCompilationError("A consulta referencia relações fora do contexto: " + ", ".join(outside_scope) + ".")
    return referenced


def compile_schema_context(
    sql: str,
    schema_lookup: Callable[[str], str],
    *,
    max_characters: int = 6_000,
) -> SchemaContext:
    """Compila o schema das relações realmente referenciadas em uma consulta."""

    return compile_relations_context(extract_relation_names(sql), schema_lookup, max_characters=max_characters)


def compile_relations_context(
    relations: Sequence[str],
    schema_lookup: Callable[[str], str],
    *,
    max_characters: int = 6_000,
) -> SchemaContext:
    """Compila relações candidatas já selecionadas pelo especialista de schema."""

    if max_characters < 256:
        raise ValueError("max_characters deve ser no mínimo 256.")
    selected: list[str] = []
    seen: set[str] = set()
    for relation in relations:
        normalized = relation.lower().strip()
        if not _IDENTIFIER.fullmatch(normalized):
            raise ContextCompilationError(f"Relação inválida: {relation!r}.")
        if normalized not in seen:
            seen.add(normalized)
            selected.append(normalized)
    if not selected:
        raise ContextCompilationError("Ao menos uma relação candidata é obrigatória.")
    fragments = []
    for relation in selected:
        ddl = schema_lookup(relation).strip()
        if not ddl:
            raise ContextCompilationError(f"Schema vazio para relação {relation!r}.")
        fragments.append(ddl)
    compiled = "\n\n".join(fragments)
    if len(compiled) > max_characters:
        raise ContextCompilationError(
            f"Contexto de {len(compiled)} caracteres excede o orçamento de {max_characters}; reduza relações ou aumente o limite conscientemente."
        )
    return SchemaContext(tuple(selected), compiled, len(compiled))
"""Diagnóstico estrutural de SQL para localizar erros além do exact match."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


def _sql(node: exp.Expression) -> str:
    return node.sql(dialect="postgres", pretty=False).lower()


def _set_sql(nodes: Iterable[exp.Expression]) -> frozenset[str]:
    return frozenset(_sql(node) for node in nodes)


def sql_components(sql: str) -> dict[str, Any]:
    tree = parse_one(sql, read="postgres")
    select = tree.find(exp.Select)
    if select is None:
        raise ParseError("Consulta sem SELECT.")
    where = tree.find(exp.Where)
    group = tree.find(exp.Group)
    order = tree.find(exp.Order)
    limit = tree.find(exp.Limit)
    return {
        "relations": frozenset(table.name.lower() for table in tree.find_all(exp.Table)),
        "projection": _set_sql(select.expressions),
        "joins": frozenset(
            (
                (join.args.get("side") or "").lower(),
                (join.args.get("kind") or "").lower(),
                _sql(join.this),
                _sql(join.args["on"]) if join.args.get("on") is not None else "",
                tuple(sorted(column.name.lower() for column in join.args.get("using", ()))),
            )
            for join in tree.find_all(exp.Join)
        ),
        "predicates": _sql(where.this) if where is not None else "",
        "group_by": _set_sql(group.expressions) if group is not None else frozenset(),
        "order_by": tuple(_sql(item) for item in order.expressions) if order is not None else (),
        "limit": _sql(limit.expression) if limit is not None and limit.expression is not None else "",
        "aggregates": frozenset(type(node).__name__.lower() for node in tree.find_all(exp.AggFunc)),
    }


def compare_sql_components(reference_sql: str, generated_sql: str) -> dict[str, bool]:
    """Compara cada componente de forma canônica; SQL inválida falha em todos."""

    reference = sql_components(reference_sql)
    try:
        generated = sql_components(generated_sql)
    except (ParseError, ValueError):
        return {name: False for name in reference}
    return {name: generated[name] == value for name, value in reference.items()}


def aggregate_component_matches(matches: Iterable[dict[str, bool]]) -> dict[str, dict[str, float | int]]:
    rows = list(matches)
    if not rows:
        raise ValueError("É necessário ao menos um resultado.")
    return {
        name: {
            "count": sum(bool(row[name]) for row in rows),
            "rate": sum(bool(row[name]) for row in rows) / len(rows),
        }
        for name in rows[0]
    }

"""Parser restrito e normalização da exportação WikiSQL do Kaggle."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import math
import re
import sqlite3
from typing import Any


_AGGREGATIONS = (None, "MAX", "MIN", "COUNT", "SUM", "AVG")
_OPERATORS = ("=", ">", "<")
_DTYPE_NAMES = {"object", "int32", "int64", "float32", "float64"}


class RestrictedReprError(ValueError):
    """Indica que a representação contém sintaxe fora da lista branca."""


def parse_restricted_numpy_repr(value: str) -> Any:
    """Converte repr de dict/list/array sem usar eval nem importar numpy."""

    if not isinstance(value, str) or not value.strip():
        raise RestrictedReprError("Representação ausente.")
    if len(value) > 20_000_000:
        raise RestrictedReprError("Representação excede o limite de tamanho.")
    try:
        tree = ast.parse(value, mode="eval")
    except SyntaxError as error:
        raise RestrictedReprError("Representação inválida.") from error
    if sum(1 for _ in ast.walk(tree)) > 2_000_000:
        raise RestrictedReprError("Representação excede o limite estrutural.")
    return _convert_node(tree.body)


def _convert_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, float, bool, type(None))):
            return node.value
        raise RestrictedReprError("Constante não permitida.")
    if isinstance(node, ast.Dict):
        if len(node.keys) != len(node.values) or any(key is None for key in node.keys):
            raise RestrictedReprError("Dict unpacking não é permitido.")
        return {_convert_node(key): _convert_node(value) for key, value in zip(node.keys, node.values)}
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_convert_node(item) for item in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        operand = _convert_node(node.operand)
        if not isinstance(operand, (int, float)) or isinstance(operand, bool):
            raise RestrictedReprError("Operador unário requer número.")
        return -operand if isinstance(node.op, ast.USub) else operand
    if isinstance(node, ast.Name) and node.id == "nan":
        return None
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id != "array":
            raise RestrictedReprError("Apenas chamadas array(...) são permitidas.")
        if len(node.args) != 1:
            raise RestrictedReprError("array(...) requer exatamente um valor.")
        for keyword in node.keywords:
            if keyword.arg != "dtype":
                raise RestrictedReprError("Keyword não permitida em array(...).")
            if not isinstance(keyword.value, ast.Name) or keyword.value.id not in _DTYPE_NAMES:
                raise RestrictedReprError("dtype não permitido.")
        return _convert_node(node.args[0])
    raise RestrictedReprError(f"Sintaxe não permitida: {type(node).__name__}.")


@dataclass(frozen=True)
class WikiSqlTable:
    identifier: str
    headers: tuple[str, ...]
    types: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]


@dataclass(frozen=True)
class WikiSqlQuery:
    selected_column: int
    aggregation: int
    condition_columns: tuple[int, ...]
    condition_operators: tuple[int, ...]
    condition_values: tuple[Any, ...]


def parse_table(value: str) -> WikiSqlTable:
    payload = parse_restricted_numpy_repr(value)
    if not isinstance(payload, dict):
        raise RestrictedReprError("Tabela deve ser um dicionário.")
    raw_headers = _required_list(payload, "header")
    raw_types = _required_list(payload, "types")
    raw_rows = _required_list(payload, "rows")
    if len(raw_headers) != len(raw_types) or not raw_headers:
        raise RestrictedReprError("Headers e tipos são incompatíveis.")
    headers = _normalize_headers(raw_headers)
    types = tuple(str(value).lower() for value in raw_types)
    if any(value not in {"text", "real"} for value in types):
        raise RestrictedReprError("Tipo WikiSQL desconhecido.")
    rows: list[tuple[Any, ...]] = []
    for row in raw_rows:
        if not isinstance(row, list) or len(row) != len(headers):
            raise RestrictedReprError("Linha incompatível com o schema.")
        rows.append(tuple(row))
    identifier = str(payload.get("name") or payload.get("id") or "").strip()
    if not identifier:
        raise RestrictedReprError("Tabela sem identificador.")
    return WikiSqlTable(identifier, headers, types, tuple(rows))


def parse_query(value: str, *, column_count: int) -> WikiSqlQuery:
    payload = parse_restricted_numpy_repr(value)
    if not isinstance(payload, dict) or not isinstance(payload.get("conds"), dict):
        raise RestrictedReprError("Consulta deve ser um dicionário estruturado.")
    conditions = payload["conds"]
    columns = tuple(_as_int(item, "índice de coluna") for item in _required_list(conditions, "column_index"))
    operators = tuple(_as_int(item, "índice de operador") for item in _required_list(conditions, "operator_index"))
    values = tuple(_required_list(conditions, "condition"))
    selected = _as_int(payload.get("sel"), "coluna selecionada")
    aggregation = _as_int(payload.get("agg"), "agregação")
    if selected not in range(column_count):
        raise RestrictedReprError("Coluna selecionada fora do schema.")
    if aggregation not in range(len(_AGGREGATIONS)):
        raise RestrictedReprError("Agregação desconhecida.")
    if not (len(columns) == len(operators) == len(values)):
        raise RestrictedReprError("Condições têm comprimentos incompatíveis.")
    if any(column not in range(column_count) for column in columns):
        raise RestrictedReprError("Condição referencia coluna fora do schema.")
    if any(operator not in range(len(_OPERATORS)) for operator in operators):
        raise RestrictedReprError("Operador de condição não suportado.")
    return WikiSqlQuery(selected, aggregation, columns, operators, values)


def render_schema(table: WikiSqlTable) -> str:
    definitions = [
        f"{quote_identifier(header)} {'TEXT' if data_type == 'text' else 'REAL'}"
        for header, data_type in zip(table.headers, table.types)
    ]
    return f"CREATE TABLE {quote_identifier(table.identifier)} (\n  " + ",\n  ".join(definitions) + "\n);"


def render_sql(table: WikiSqlTable, query: WikiSqlQuery) -> str:
    selected = quote_identifier(table.headers[query.selected_column])
    aggregation = _AGGREGATIONS[query.aggregation]
    projection = selected if aggregation is None else f"{aggregation}({selected})"
    sql = f"SELECT {projection} FROM {quote_identifier(table.identifier)}"
    predicates = []
    for column_index, operator_index, value in zip(
        query.condition_columns,
        query.condition_operators,
        query.condition_values,
    ):
        column = quote_identifier(table.headers[column_index])
        operator = _OPERATORS[operator_index]
        literal = _render_literal(value, table.types[column_index])
        predicates.append(f"{column} {operator} {literal}")
    if predicates:
        sql += " WHERE " + " AND ".join(predicates)
    return sql


def execute_reference(table: WikiSqlTable, sql: str) -> tuple[tuple[Any, ...], ...]:
    """Executa uma referência em memória para detectar schema/SQL inválidos."""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(render_schema(table))
        placeholders = ", ".join("?" for _ in table.headers)
        connection.executemany(
            f"INSERT INTO {quote_identifier(table.identifier)} VALUES ({placeholders})",
            table.rows,
        )
        return tuple(tuple(value for value in row) for row in connection.execute(sql).fetchall())
    finally:
        connection.close()


def quote_identifier(value: str) -> str:
    cleaned = value.replace("\x00", "").strip()
    if not cleaned:
        raise RestrictedReprError("Identificador vazio.")
    return '"' + cleaned.replace('"', '""') + '"'


def _required_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise RestrictedReprError(f"Campo {key} deve ser uma lista.")
    return value


def _as_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RestrictedReprError(f"{label} deve ser inteiro.")
    return value


def _normalize_headers(values: list[Any]) -> tuple[str, ...]:
    headers: list[str] = []
    occurrences: dict[str, int] = {}
    for index, value in enumerate(values, start=1):
        header = re.sub(r"\s+", " ", str(value).replace("\x00", " ")).strip() or f"column_{index}"
        key = header.casefold()
        occurrences[key] = occurrences.get(key, 0) + 1
        if occurrences[key] > 1:
            header = f"{header}__{occurrences[key]}"
        headers.append(header)
    return tuple(headers)


def _render_literal(value: Any, data_type: str) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NULL"
    if data_type == "real" and not isinstance(value, bool):
        try:
            number = float(value)
        except (TypeError, ValueError):
            pass
        else:
            if math.isfinite(number):
                return str(int(number)) if number.is_integer() else repr(number)
    return "'" + str(value).replace("'", "''") + "'"

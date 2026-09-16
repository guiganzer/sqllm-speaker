"""Métricas estruturais reproduzíveis para avaliação de Text-to-SQL."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Sequence

from sqlglot import exp, parse, parse_one
from sqlglot.errors import ParseError

from llm_to_sql.agentic.policy import ReadOnlySqlPolicy


@dataclass(frozen=True)
class SqlAssessment:
    """Resultado de validações estruturais que não exigem executar SQL."""

    parses: bool
    sql_only: bool
    policy_allowed: bool
    tables_valid: bool
    columns_valid: bool

    @property
    def schema_references_valid(self) -> bool:
        return self.tables_valid and self.columns_valid


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[\[\]`\"']", "", value).strip().lower()


def normalize_model_output(output: str) -> str:
    """Remove somente delimitadores de raciocínio do protocolo Qwen, nunca prosa livre."""

    normalized = output.strip()
    normalized = re.sub(r"^\s*<think>.*?</think>\s*", "", normalized, flags=re.IGNORECASE | re.DOTALL)
    normalized = re.sub(r"^\s*</think>\s*", "", normalized, flags=re.IGNORECASE)
    return normalized.strip()


def canonical_sql(sql: str) -> str | None:
    """Forma estável para exact match suplementar; não prova equivalência semântica."""

    policy = ReadOnlySqlPolicy().validate(normalize_model_output(sql))
    if not policy.allowed or policy.normalized_sql is None:
        return None
    try:
        return parse_one(policy.normalized_sql).sql(pretty=False)
    except ParseError:
        return None


def extract_schema_identifiers(ddl: str) -> tuple[set[str], set[str]]:
    """Extrai tabelas e colunas do DDL aceito, tolerando dialetos mistos."""

    tables: set[str] = set()
    columns: set[str] = set()
    for statement in parse(ddl, error_level="ignore"):
        for create in statement.find_all(exp.Create):
            schema = create.this
            table = schema.this if isinstance(schema, exp.Schema) else schema
            if isinstance(table, exp.Table):
                tables.add(_normalize_identifier(table.name))
            if isinstance(schema, exp.Schema):
                for definition in schema.expressions:
                    if isinstance(definition, exp.ColumnDef):
                        columns.add(_normalize_identifier(definition.name))
    return tables, columns


def assess_sql(sql: str, ddl: str) -> SqlAssessment:
    """Verifica parse, pureza da saída, política e referências ao schema fornecido."""

    policy = ReadOnlySqlPolicy().validate(sql)
    if not policy.allowed or policy.normalized_sql is None:
        return SqlAssessment(False, False, False, False, False)
    try:
        query = parse_one(policy.normalized_sql)
    except ParseError:
        return SqlAssessment(False, False, True, False, False)

    tables, columns = extract_schema_identifiers(ddl)
    # O dataset fonte usa aspas duplas também para literais textuais (dialeto SQLite permissivo).
    # SQLGlot os trata como identificadores em alguns dialetos, o que criaria falsos negativos.
    quoted_text_values = {_normalize_identifier(value) for value in re.findall(r'"([^\"]+)"', policy.normalized_sql)}
    cte_aliases = {_normalize_identifier(cte.alias_or_name) for cte in query.find_all(exp.CTE)}
    referenced_tables = {
        _normalize_identifier(table.name)
        for table in query.find_all(exp.Table)
        if _normalize_identifier(table.name) not in cte_aliases
    }
    referenced_columns = {
        _normalize_identifier(column.name)
        for column in query.find_all(exp.Column)
        if column.name and column.name != "*" and _normalize_identifier(column.name) not in quoted_text_values
    }
    return SqlAssessment(
        parses=True,
        sql_only=True,
        policy_allowed=True,
        tables_valid=referenced_tables.issubset(tables),
        columns_valid=referenced_columns.issubset(columns),
    )


def complexity_bucket(reference_sql: str) -> str:
    """Agrupa referências em três níveis para uma amostra de avaliação equilibrada."""

    try:
        query = parse_one(reference_sql)
    except ParseError:
        return "complexa"
    table_count = len(list(query.find_all(exp.Table)))
    if query.find(exp.Join) or query.find(exp.Subquery) or query.args.get("group"):
        return "complexa"
    if table_count > 1 or query.args.get("order") or query.args.get("limit"):
        return "intermediaria"
    return "simples"


def _record_key(record: dict[str, Any]) -> str:
    message_text = "\n".join(message["content"] for message in record["messages"])
    payload = json.dumps({"schema_group": record.get("schema_group"), "messages": message_text}, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def deterministic_stratified_sample(records: Sequence[dict[str, Any]], sample_size: int) -> list[dict[str, Any]]:
    """Seleciona registros estáveis e aproximadamente equilibrados por complexidade."""

    if sample_size <= 0:
        raise ValueError("sample_size deve ser positivo")
    buckets: dict[str, list[dict[str, Any]]] = {"simples": [], "intermediaria": [], "complexa": []}
    for record in records:
        buckets[complexity_bucket(record["messages"][-1]["content"])].append(record)
    for bucket in buckets.values():
        bucket.sort(key=_record_key)

    available = [name for name, bucket in buckets.items() if bucket]
    selected: list[dict[str, Any]] = []
    quota = sample_size // len(available)
    for name in available:
        selected.extend(buckets[name][:quota])
        buckets[name] = buckets[name][quota:]
    remaining = sample_size - len(selected)
    for name in available:
        if not remaining:
            break
        taken = buckets[name][:remaining]
        selected.extend(taken)
        remaining -= len(taken)
    return sorted(selected, key=_record_key)


def aggregate_assessments(assessments: Iterable[SqlAssessment]) -> dict[str, float | int]:
    values = list(assessments)
    if not values:
        raise ValueError("Não é possível agregar uma avaliação vazia")
    total = len(values)
    metrics: dict[str, float | int] = {"examples": total}
    for name in ("parses", "sql_only", "policy_allowed", "schema_references_valid"):
        accepted = sum(bool(getattr(value, name)) for value in values)
        metrics[f"{name}_count"] = accepted
        metrics[f"{name}_rate"] = accepted / total
    return metrics

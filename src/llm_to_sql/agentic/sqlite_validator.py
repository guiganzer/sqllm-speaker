"""Validação e execução estritamente read-only sobre um banco SQLite local."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import sqlite3
from typing import Any

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from llm_to_sql.agentic.policy import ReadOnlySqlPolicy
from llm_to_sql.schema_catalog import SchemaCatalog


@dataclass(frozen=True)
class SqlValidationResult:
    approved: bool
    executed: bool
    reason: str
    normalized_sql: str | None
    relations: tuple[str, ...] = ()
    rows: tuple[tuple[Any, ...], ...] = ()
    truncated: bool = False
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class SqliteCatalogValidator:
    def __init__(
        self,
        *,
        catalog: SchemaCatalog,
        database_path: Path,
        max_virtual_machine_steps: int = 50_000_000,
    ) -> None:
        if catalog.dialect != "sqlite":
            raise ValueError("SqliteCatalogValidator requer catálogo sqlite.")
        if not database_path.is_file():
            raise ValueError(f"Banco SQLite não encontrado: {database_path}")
        if max_virtual_machine_steps < 10_000:
            raise ValueError("Limite de passos SQLite muito baixo.")
        self.catalog = catalog
        self.database_path = database_path
        self.max_virtual_machine_steps = max_virtual_machine_steps
        self.policy = ReadOnlySqlPolicy()

    def validate_and_execute(self, sql: str, *, pack_name: str, max_rows: int = 100) -> SqlValidationResult:
        if not 1 <= max_rows <= 1_000:
            raise ValueError("max_rows deve estar entre 1 e 1000.")
        policy = self.policy.validate(sql)
        if not policy.allowed or policy.normalized_sql is None:
            return SqlValidationResult(False, False, policy.reason, None)
        try:
            expression = parse_one(policy.normalized_sql, read="sqlite")
        except ParseError as error:
            return SqlValidationResult(False, False, "SQL não fez parse como SQLite.", policy.normalized_sql, error=str(error)[:500])
        cte_names = {cte.alias_or_name.lower() for cte in expression.find_all(exp.CTE) if cte.alias_or_name}
        relations = tuple(dict.fromkeys(table.name.lower() for table in expression.find_all(exp.Table) if table.name.lower() not in cte_names))
        allowed = set(self.catalog.pack(pack_name).tables)
        outside = sorted(set(relations) - allowed)
        if not relations:
            return SqlValidationResult(False, False, "A consulta não referencia tabela conhecida.", policy.normalized_sql)
        if outside:
            return SqlValidationResult(
                False,
                False,
                "Relações fora do pack: " + ", ".join(outside),
                policy.normalized_sql,
                relations,
            )
        connection = sqlite3.connect(f"file:{self.database_path.resolve()}?mode=ro", uri=True)
        try:
            connection.execute("PRAGMA query_only = ON")
            calls = 0

            def progress() -> int:
                nonlocal calls
                calls += 1
                return int(calls * 1_000 > self.max_virtual_machine_steps)

            connection.set_progress_handler(progress, 1_000)
            cursor = connection.execute(policy.normalized_sql)
            rows = cursor.fetchmany(max_rows + 1)
            truncated = len(rows) > max_rows
            return SqlValidationResult(
                True,
                True,
                "Consulta aprovada e executada em conexão SQLite somente leitura.",
                policy.normalized_sql,
                relations,
                tuple(tuple(value for value in row) for row in rows[:max_rows]),
                truncated,
            )
        except sqlite3.Error as error:
            return SqlValidationResult(
                True,
                False,
                "Consulta aprovada, mas a execução falhou.",
                policy.normalized_sql,
                relations,
                error=str(error)[:500],
            )
        finally:
            connection.close()

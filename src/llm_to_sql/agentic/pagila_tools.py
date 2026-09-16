"""Ferramentas reais, limitadas e auditáveis para o experimento Pagila local."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
import subprocess
from typing import Any

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from .policy import ReadOnlySqlPolicy


_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class SqlExecution:
    approved: bool
    reason: str
    sql: str | None
    rows: tuple[tuple[str, ...], ...] = ()
    truncated: bool = False
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class PagilaAgentTools:
    """Ponte Docker para Pagila; usa a conta sqllm_readonly e nunca executa escrita."""

    def __init__(
        self,
        *,
        container: str = "sqllm-pagila-postgres",
        database: str = "pagila",
        role: str = "sqllm_readonly",
        statement_timeout_ms: int = 5_000,
    ) -> None:
        if statement_timeout_ms < 100 or statement_timeout_ms > 30_000:
            raise ValueError("statement_timeout_ms deve estar entre 100 e 30000.")
        self.container = container
        self.database = database
        self.role = role
        self.statement_timeout_ms = statement_timeout_ms
        self.policy = ReadOnlySqlPolicy()

    def get_database_profile(self) -> dict[str, Any]:
        rows = self._run_tsv(
            "SELECT current_setting('server_version'), "
            "(SELECT count(*) FROM pg_tables WHERE schemaname = 'public'), "
            "(SELECT count(*) FROM pg_views WHERE schemaname = 'public'), "
            "(SELECT count(*) FROM film)"
        )
        if len(rows) != 1 or len(rows[0]) != 4:
            raise RuntimeError("Perfil do Pagila retornou formato inesperado.")
        version, tables, views, films = rows[0]
        return {
            "dialect": "postgres",
            "database": self.database,
            "server_version": version,
            "public_tables": int(tables),
            "public_views": int(views),
            "descriptive_films": int(films),
            "execution_role": self.role,
            "read_only": True,
        }

    def get_table_schema(self, table_name: str) -> str:
        if not _IDENTIFIER.fullmatch(table_name):
            raise ValueError("Nome de tabela inválido.")
        query = (
            "SELECT column_name, data_type, is_nullable, COALESCE(column_default, '') "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = '" + table_name + "' "
            "ORDER BY ordinal_position"
        )
        rows = self._run_tsv(query)
        if not rows:
            raise ValueError(f"Tabela ou view não encontrada: {table_name}")
        definitions = []
        for name, data_type, nullable, default in rows:
            definition = f"{name} {data_type}"
            if nullable == "NO":
                definition += " NOT NULL"
            if default:
                definition += f" DEFAULT {default}"
            definitions.append(definition)
        return "CREATE TABLE public." + table_name + " (\n  " + ",\n  ".join(definitions) + "\n);"

    def execute_readonly_sql(self, sql: str, *, max_rows: int = 100) -> SqlExecution:
        if not 1 <= max_rows <= 1_000:
            raise ValueError("max_rows deve estar entre 1 e 1000.")
        policy = self.policy.validate(sql)
        if not policy.allowed or policy.normalized_sql is None:
            return SqlExecution(False, policy.reason, None)
        try:
            expression = parse_one(policy.normalized_sql, read="postgres")
        except ParseError:
            return SqlExecution(False, "A consulta não fez parse como PostgreSQL.", policy.normalized_sql)
        is_explain = policy.normalized_sql.upper().startswith("EXPLAIN")
        if is_explain:
            executable = policy.normalized_sql
        elif expression.find(exp.Select):
            executable = f"SELECT * FROM ({policy.normalized_sql}) AS sqllm_limited_result LIMIT {max_rows}"
        else:
            return SqlExecution(False, "A execução agentic aceita SELECT, WITH ou EXPLAIN.", policy.normalized_sql)
        try:
            rows = self._run_tsv(executable)
        except subprocess.CalledProcessError as error:
            return SqlExecution(
                True,
                "Consulta aprovada, mas a execução falhou.",
                policy.normalized_sql,
                error=self._sanitize_error(error.stderr),
            )
        truncated = len(rows) >= max_rows and not is_explain
        return SqlExecution(True, "Consulta executada com conta somente leitura.", policy.normalized_sql, tuple(rows), truncated)

    def _run_tsv(self, sql: str) -> list[tuple[str, ...]]:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "-e",
                f"PGOPTIONS=-c statement_timeout={self.statement_timeout_ms}",
                self.container,
                "psql",
                "-v",
                "ON_ERROR_STOP=1",
                "-P",
                "pager=off",
                "-U",
                self.role,
                "-d",
                self.database,
                "-At",
                "-F",
                "\t",
                "-c",
                sql,
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return [tuple(line.split("\t")) for line in result.stdout.splitlines() if line]

    @staticmethod
    def _sanitize_error(value: str | None) -> str:
        if not value:
            return "Erro de banco sem detalhe disponível."
        lines = [line.strip() for line in value.splitlines() if "ERROR:" in line or "permission denied" in line.lower()]
        return " ".join(lines)[:500] or "Erro de banco sem detalhe disponível."

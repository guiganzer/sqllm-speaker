"""Política conservadora para impedir escrita e múltiplas statements."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SqlPolicyResult:
    allowed: bool
    reason: str
    normalized_sql: str | None = None


class ReadOnlySqlPolicy:
    """Validação lexical defensiva; não substitui permissões read-only no banco."""

    _allowed_roots = re.compile(r"^(SELECT|WITH|EXPLAIN)\b", re.IGNORECASE)
    _forbidden = re.compile(
        r"\b(INSERT|UPDATE|DELETE|MERGE|UPSERT|REPLACE|DROP|ALTER|CREATE|TRUNCATE|"
        r"GRANT|REVOKE|COMMIT|ROLLBACK|BEGIN|VACUUM|ATTACH|DETACH|PRAGMA|CALL|EXEC)\b",
        re.IGNORECASE,
    )
    _block_comments = re.compile(r"/\*.*?\*/", re.DOTALL)
    _line_comments = re.compile(r"--[^\r\n]*")

    def validate(self, sql: str) -> SqlPolicyResult:
        if not isinstance(sql, str) or not sql.strip():
            return SqlPolicyResult(False, "SQL ausente.")

        normalized = self._strip_comments(sql).strip()
        statements = [part.strip() for part in normalized.split(";") if part.strip()]
        if len(statements) != 1:
            return SqlPolicyResult(False, "A execução aceita exatamente uma statement SQL.")

        statement = statements[0]
        if self._forbidden.search(statement):
            return SqlPolicyResult(False, "A consulta contém operação fora da política de leitura.")
        if not self._allowed_roots.match(statement):
            return SqlPolicyResult(False, "A consulta deve iniciar com SELECT, WITH ou EXPLAIN.")
        return SqlPolicyResult(True, "Consulta aprovada pela política local.", statement)

    def _strip_comments(self, sql: str) -> str:
        without_blocks = self._block_comments.sub(" ", sql)
        return self._line_comments.sub(" ", without_blocks)

"""Máquina de estados independente de LLM e driver de banco."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .policy import ReadOnlySqlPolicy, SqlPolicyResult


class SessionStage(StrEnum):
    AWAITING_SCHEMA = "awaiting_schema"
    AWAITING_SQL = "awaiting_sql"
    AWAITING_EXECUTION = "awaiting_execution"
    REPAIRING = "repairing"
    FINALIZED = "finalized"
    BLOCKED = "blocked"


@dataclass
class AgenticSession:
    question: str
    stage: SessionStage = SessionStage.AWAITING_SCHEMA
    table_schemas: dict[str, str] = field(default_factory=dict)
    sql: str | None = None
    repairs: int = 0
    final_reason: str | None = None


class AgenticWorkflow:
    """Controla a ordem das ações; integrações chamam LLM e ferramentas fora daqui."""

    def __init__(self, policy: ReadOnlySqlPolicy | None = None, max_repairs: int = 2) -> None:
        if max_repairs < 0:
            raise ValueError("max_repairs não pode ser negativo")
        self.policy = policy or ReadOnlySqlPolicy()
        self.max_repairs = max_repairs

    def begin(self, question: str) -> AgenticSession:
        if not question or not question.strip():
            raise ValueError("A pergunta não pode estar vazia")
        return AgenticSession(question=question.strip())

    def add_schema(self, session: AgenticSession, table_name: str, ddl: str) -> None:
        self.add_schemas(session, {table_name: ddl})

    def add_schemas(self, session: AgenticSession, schemas: dict[str, str]) -> None:
        """Conclui uma rodada de descoberta com uma ou mais relações antes do autor SQL atuar."""

        self._require_stage(session, SessionStage.AWAITING_SCHEMA, SessionStage.REPAIRING)
        if not schemas:
            raise ValueError("Ao menos um schema é obrigatório")
        for table_name, ddl in schemas.items():
            if not table_name.strip() or not ddl.strip():
                raise ValueError("table_name e ddl são obrigatórios")
            session.table_schemas[table_name] = ddl
        session.stage = SessionStage.AWAITING_SQL

    def submit_sql(self, session: AgenticSession, sql: str) -> SqlPolicyResult:
        self._require_stage(session, SessionStage.AWAITING_SQL, SessionStage.REPAIRING)
        result = self.policy.validate(sql)
        if result.allowed:
            session.sql = result.normalized_sql
            session.stage = SessionStage.AWAITING_EXECUTION
        else:
            session.final_reason = result.reason
            session.stage = SessionStage.BLOCKED
        return result

    def record_validation_failure(self, session: AgenticSession, sanitized_error: str) -> None:
        """Solicita um único reparo para SQL que falhou antes da execução."""

        self._require_stage(session, SessionStage.AWAITING_SQL)
        if not sanitized_error.strip():
            raise ValueError("sanitized_error é obrigatório.")
        if session.repairs >= self.max_repairs:
            session.stage = SessionStage.BLOCKED
            session.final_reason = "Limite de reparos atingido."
            return
        session.repairs += 1
        session.stage = SessionStage.REPAIRING
        session.final_reason = sanitized_error.strip()
    def record_execution(self, session: AgenticSession, *, succeeded: bool, sanitized_error: str | None = None) -> None:
        self._require_stage(session, SessionStage.AWAITING_EXECUTION)
        if succeeded:
            session.stage = SessionStage.FINALIZED
            session.final_reason = "Consulta executada com sucesso."
            return
        if session.repairs >= self.max_repairs:
            session.stage = SessionStage.BLOCKED
            session.final_reason = "Limite de reparos atingido."
            return
        session.repairs += 1
        session.stage = SessionStage.REPAIRING
        session.final_reason = sanitized_error or "A execução falhou sem detalhe disponível."

    def finalize_without_execution(self, session: AgenticSession, reason: str) -> None:
        self._require_stage(session, SessionStage.AWAITING_SCHEMA, SessionStage.AWAITING_SQL, SessionStage.REPAIRING)
        session.stage = SessionStage.FINALIZED
        session.final_reason = reason

    @staticmethod
    def _require_stage(session: AgenticSession, *allowed: SessionStage) -> None:
        if session.stage not in allowed:
            names = ", ".join(stage.value for stage in allowed)
            raise RuntimeError(f"Ação inválida no estado {session.stage}; esperado: {names}.")

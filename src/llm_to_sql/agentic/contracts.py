"""Contratos estáveis entre o modelo, agentes e ferramentas do runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AgentRole(StrEnum):
    ORCHESTRATOR = "orchestrator"
    SCHEMA_SPECIALIST = "schema_specialist"
    SQL_AUTHOR = "sql_author"
    POLICY_GUARDIAN = "policy_guardian"
    SQL_REPAIRER = "sql_repairer"
    FINALIZER = "finalizer"


class ToolName(StrEnum):
    GET_DATABASE_PROFILE = "get_database_profile"
    GET_TABLE_SCHEMA = "get_table_schema"
    EXECUTE_READONLY_SQL = "execute_readonly_sql"


@dataclass(frozen=True)
class RoleSpec:
    """Descrição auditável de um papel lógico; não instancia outro modelo."""

    role: AgentRole
    objective: str
    allowed_tools: tuple[ToolName, ...] = ()


ROLE_SPECS: tuple[RoleSpec, ...] = (
    RoleSpec(AgentRole.ORCHESTRATOR, "Controlar estados e limites; não inventar SQL."),
    RoleSpec(
        AgentRole.SCHEMA_SPECIALIST,
        "Obter somente metadados necessários para responder à pergunta.",
        (ToolName.GET_DATABASE_PROFILE, ToolName.GET_TABLE_SCHEMA),
    ),
    RoleSpec(AgentRole.SQL_AUTHOR, "Gerar uma única consulta SQL a partir do schema disponível."),
    RoleSpec(AgentRole.POLICY_GUARDIAN, "Aplicar política local de SQL; este papel é código determinístico."),
    RoleSpec(AgentRole.SQL_REPAIRER, "Reparar SQL usando erro sanitizado e schema já obtido."),
    RoleSpec(AgentRole.FINALIZER, "Encerrar com SQL, esclarecimento ou abstenção verificável."),
)


TOOL_SCHEMAS: dict[ToolName, dict[str, Any]] = {
    ToolName.GET_DATABASE_PROFILE: {
        "name": ToolName.GET_DATABASE_PROFILE,
        "description": "Retorna dialeto e inventário resumido autorizado do banco ativo.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    ToolName.GET_TABLE_SCHEMA: {
        "name": ToolName.GET_TABLE_SCHEMA,
        "description": "Retorna DDL e metadados autorizados de uma tabela conhecida.",
        "parameters": {
            "type": "object",
            "properties": {"table_name": {"type": "string", "minLength": 1}},
            "required": ["table_name"],
            "additionalProperties": False,
        },
    },
    ToolName.EXECUTE_READONLY_SQL: {
        "name": ToolName.EXECUTE_READONLY_SQL,
        "description": "Executa uma consulta aprovada, com credencial read-only e linhas limitadas.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "minLength": 1},
                "max_rows": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["sql", "max_rows"],
            "additionalProperties": False,
        },
    },
}

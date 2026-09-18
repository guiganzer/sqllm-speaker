"""Catálogo versionado de tabelas, relacionamentos e subgrafos de schema."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class CatalogTable:
    name: str
    columns: tuple[tuple[str, str], ...]
    primary_key: tuple[str, ...]


@dataclass(frozen=True)
class CatalogRelationship:
    from_table: str
    from_columns: tuple[str, ...]
    to_table: str
    to_columns: tuple[str, ...]
    kind: str
    note: str = ""


@dataclass(frozen=True)
class RelationPack:
    name: str
    tier: str
    tables: tuple[str, ...]
    purpose: str


@dataclass(frozen=True)
class SchemaCatalog:
    name: str
    dialect: str
    database_path: str | None
    tables: dict[str, CatalogTable]
    relationships: tuple[CatalogRelationship, ...]
    packs: dict[str, RelationPack]
    source: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "SchemaCatalog":
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SchemaCatalog":
        tables = {
            name: CatalogTable(
                name=name,
                columns=tuple((column["name"], column["type"]) for column in value["columns"]),
                primary_key=tuple(value.get("primary_key", ())),
            )
            for name, value in payload["tables"].items()
        }
        relationships = tuple(
            CatalogRelationship(
                from_table=value["from_table"],
                from_columns=tuple(value["from_columns"]),
                to_table=value["to_table"],
                to_columns=tuple(value["to_columns"]),
                kind=value["kind"],
                note=value.get("note", ""),
            )
            for value in payload.get("relationships", ())
        )
        packs = {
            name: RelationPack(
                name=name,
                tier=value["tier"],
                tables=tuple(value["tables"]),
                purpose=value["purpose"],
            )
            for name, value in payload["packs"].items()
        }
        catalog = cls(
            name=payload["name"],
            dialect=payload["dialect"],
            database_path=payload.get("database_path"),
            tables=tables,
            relationships=relationships,
            packs=packs,
            source=dict(payload.get("source", {})),
        )
        catalog.validate()
        return catalog

    def validate(self) -> None:
        if not _IDENTIFIER.fullmatch(self.name):
            raise ValueError("Nome de catálogo inválido.")
        if self.dialect not in {"sqlite", "postgres"}:
            raise ValueError("Dialeto deve ser sqlite ou postgres.")
        for table in self.tables.values():
            if not _IDENTIFIER.fullmatch(table.name):
                raise ValueError(f"Tabela inválida: {table.name}")
            column_names = {name for name, _ in table.columns}
            if not column_names or any(not _IDENTIFIER.fullmatch(name) for name in column_names):
                raise ValueError(f"Colunas inválidas em {table.name}.")
            if not set(table.primary_key) <= column_names:
                raise ValueError(f"PK inválida em {table.name}.")
        for relationship in self.relationships:
            if relationship.kind not in {"hard", "soft"}:
                raise ValueError("Relacionamento deve ser hard ou soft.")
            if relationship.from_table not in self.tables or relationship.to_table not in self.tables:
                raise ValueError("Relacionamento referencia tabela ausente.")
            source = {name for name, _ in self.tables[relationship.from_table].columns}
            target = {name for name, _ in self.tables[relationship.to_table].columns}
            if not set(relationship.from_columns) <= source or not set(relationship.to_columns) <= target:
                raise ValueError("Relacionamento referencia coluna ausente.")
            if len(relationship.from_columns) != len(relationship.to_columns):
                raise ValueError("Relacionamento tem cardinalidade de colunas incompatível.")
        for pack in self.packs.values():
            if pack.tier not in {"small", "medium", "heavy"}:
                raise ValueError(f"Tier inválido em {pack.name}.")
            if not pack.tables or not set(pack.tables) <= set(self.tables):
                raise ValueError(f"Pack inválido: {pack.name}.")
            if len(set(pack.tables)) != len(pack.tables):
                raise ValueError(f"Pack contém tabela repetida: {pack.name}.")

    def pack(self, name: str) -> RelationPack:
        try:
            return self.packs[name]
        except KeyError as error:
            raise KeyError(f"Pack desconhecido: {name}") from error

    def relationships_for(self, table_names: tuple[str, ...]) -> tuple[CatalogRelationship, ...]:
        selected = set(table_names)
        return tuple(
            relationship
            for relationship in self.relationships
            if relationship.from_table in selected and relationship.to_table in selected
        )

    def render_pack(self, name: str) -> str:
        pack = self.pack(name)
        fragments: list[str] = [
            f"-- catalog: {self.name}",
            f"-- dialect: {self.dialect}",
            f"-- relation_pack: {pack.name} ({pack.tier})",
        ]
        for table_name in pack.tables:
            table = self.tables[table_name]
            definitions = [f"{column} {data_type}" for column, data_type in table.columns]
            if table.primary_key:
                definitions.append("PRIMARY KEY (" + ", ".join(table.primary_key) + ")")
            fragments.append(
                "CREATE TABLE " + table.name + " (\n  " + ",\n  ".join(definitions) + "\n);"
            )
        for relationship in self.relationships_for(pack.tables):
            arrow = "->" if relationship.kind == "hard" else "~>"
            line = (
                f"-- {relationship.kind} relationship: "
                f"{relationship.from_table}.{','.join(relationship.from_columns)} "
                f"{arrow} {relationship.to_table}.{','.join(relationship.to_columns)}"
            )
            if relationship.note:
                line += f" ({relationship.note})"
            fragments.append(line)
        return "\n\n".join(fragments)

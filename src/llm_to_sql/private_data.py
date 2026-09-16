"""Preparação segura e reproduzível de exemplos privados para a fase 2."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from sqlglot import parse_one
from sqlglot.errors import ParseError

from llm_to_sql.agentic.policy import ReadOnlySqlPolicy


SYSTEM_PROMPT = (
    "Você é um assistente especializado em SQL. Gere somente uma consulta SQL "
    "de leitura compatível com o schema fornecido. Não explique a resposta."
)


@dataclass(frozen=True)
class EndpointSnapshot:
    endpoint_id: str
    ddl: str
    snapshot_id: str


@dataclass(frozen=True)
class PrivatePreparationReport:
    created_at_utc: str
    source_rows: int
    accepted_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    schema_snapshots: int
    dynamic_endpoint_rows: int
    dialect: str
    split_strategy: str
    rejected: dict[str, int]
    queries_path: str
    base_schema_path: str
    endpoint_manifest_path: str | None
    processed_path: str


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_sql_or_ddl(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def fingerprint(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"JSONL inválido em {path.name}, linha {line_number}.") from error
        if not isinstance(row, Mapping):
            raise ValueError(f"A linha {line_number} de {path.name} deve ser um objeto JSON.")
        rows.append(row)
    if not rows:
        raise ValueError(f"Nenhuma linha JSON encontrada em {path}.")
    return rows


def read_schema(path: Path) -> str:
    schema = normalize_sql_or_ddl(path.read_text(encoding="utf-8-sig"))
    if not schema:
        raise ValueError(f"Schema vazio: {path}")
    return schema


def load_endpoint_snapshots(manifest_path: Path) -> dict[str, EndpointSnapshot]:
    """Carrega snapshots dinâmicos sem permitir que o manifest aponte fora da pasta privada."""

    root = manifest_path.parent.resolve()
    snapshots: dict[str, EndpointSnapshot] = {}
    for row in read_jsonl(manifest_path):
        endpoint_id = row.get("endpoint_id")
        relative_schema_path = row.get("schema_path")
        if not isinstance(endpoint_id, str) or not endpoint_id.strip():
            raise ValueError("Todo endpoint do manifest deve ter endpoint_id não vazio.")
        if not isinstance(relative_schema_path, str) or not relative_schema_path.strip():
            raise ValueError(f"Endpoint {endpoint_id!r} sem schema_path.")
        schema_path = (root / relative_schema_path).resolve()
        if not schema_path.is_relative_to(root):
            raise ValueError(f"schema_path de {endpoint_id!r} deve permanecer dentro da pasta privada.")
        if endpoint_id in snapshots:
            raise ValueError(f"endpoint_id duplicado no manifest: {endpoint_id!r}.")
        ddl = read_schema(schema_path)
        snapshots[endpoint_id] = EndpointSnapshot(endpoint_id, ddl, fingerprint(ddl))
    return snapshots


def _source_metadata(row: Mapping[str, Any], dialect: str) -> dict[str, str]:
    metadata = {"dialect": dialect}
    for field in ("id", "categoria", "dificuldade"):
        value = row.get(field)
        if isinstance(value, (str, int, float)):
            metadata[field] = str(value)
    return metadata


def _record_key(question: str, sql: str, snapshot_id: str) -> str:
    return fingerprint("\x1f".join((question.lower(), sql.lower(), snapshot_id)))


def _split_name(record: Mapping[str, Any], validation_percent: int, test_percent: int) -> str:
    material = "\x1f".join(
        (
            record["schema_snapshot_id"],
            record["messages"][1]["content"],
            record["messages"][2]["content"],
        )
    )
    bucket = int(fingerprint(material)[:8], 16) % 100
    if bucket < test_percent:
        return "test"
    if bucket < test_percent + validation_percent:
        return "validation"
    return "train"


def build_private_examples(
    rows: Iterable[Mapping[str, Any]],
    *,
    base_schema: str,
    endpoint_snapshots: Mapping[str, EndpointSnapshot] | None,
    dialect: str,
    max_characters: int,
    max_schema_characters: int,
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    """Valida exemplos privados e os converte para o contrato de SFT com snapshot por consulta."""

    policy = ReadOnlySqlPolicy()
    snapshots = {"base": EndpointSnapshot("base", base_schema, fingerprint(base_schema))}
    snapshots.update(endpoint_snapshots or {})
    seen: set[str] = set()
    rejected: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    dynamic_endpoint_rows = 0

    for row in rows:
        question_raw = row.get("pergunta")
        sql_raw = row.get("sql")
        if not isinstance(question_raw, str) or not question_raw.strip() or not isinstance(sql_raw, str) or not sql_raw.strip():
            rejected["missing_required_field"] += 1
            continue
        if "somente_leitura" in row and row["somente_leitura"] is not True:
            rejected["not_marked_readonly"] += 1
            continue
        endpoint_id = row.get("endpoint_id", "base")
        if not isinstance(endpoint_id, str) or endpoint_id not in snapshots:
            rejected["unknown_endpoint"] += 1
            continue
        question = normalize_text(question_raw)
        policy_result = policy.validate(normalize_sql_or_ddl(sql_raw))
        if not policy_result.allowed or policy_result.normalized_sql is None:
            rejected["read_only_policy"] += 1
            continue
        sql = policy_result.normalized_sql
        snapshot = snapshots[endpoint_id]
        if len(snapshot.ddl) > max_schema_characters:
            rejected["schema_context_too_large"] += 1
            continue
        if max(len(question), len(sql)) > max_characters:
            rejected["question_or_sql_too_large"] += 1
            continue
        try:
            parse_one(sql, read=dialect)
        except ParseError:
            rejected["invalid_sql_for_dialect"] += 1
            continue
        key = _record_key(question, sql, snapshot.snapshot_id)
        if key in seen:
            rejected["duplicate"] += 1
            continue
        seen.add(key)
        if endpoint_id != "base":
            dynamic_endpoint_rows += 1
        user = f"<schema>\n{snapshot.ddl}\n</schema>\n\n<pergunta>\n{question}\n</pergunta>"
        examples.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": sql},
                ],
                "schema_group": snapshot.snapshot_id,
                "schema_snapshot_id": snapshot.snapshot_id,
                "endpoint_id": endpoint_id,
                "source": _source_metadata(row, dialect),
            }
        )
    return examples, rejected, dynamic_endpoint_rows


def split_private_examples(
    examples: Iterable[Mapping[str, Any]], *, validation_percent: int, test_percent: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not 1 <= validation_percent <= 40 or not 1 <= test_percent <= 40 or validation_percent + test_percent >= 50:
        raise ValueError("validation_percent e test_percent devem estar entre 1 e 40 e somar menos de 50.")
    train: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for example in examples:
        target = _split_name(example, validation_percent, test_percent)
        copied = dict(example)
        if target == "train":
            train.append(copied)
        elif target == "validation":
            validation.append(copied)
        else:
            test.append(copied)
    return train, validation, test


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            output.write("\n")


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def prepare_private_dataset(
    *,
    root_dir: Path,
    queries_path: Path,
    base_schema_path: Path,
    endpoint_manifest_path: Path | None,
    dialect: str,
    validation_percent: int,
    test_percent: int,
    max_characters: int,
    max_schema_characters: int,
    output_label: str,
) -> PrivatePreparationReport:
    base_schema = read_schema(base_schema_path)
    endpoint_snapshots = load_endpoint_snapshots(endpoint_manifest_path) if endpoint_manifest_path else None
    rows = read_jsonl(queries_path)
    examples, rejected, dynamic_endpoint_rows = build_private_examples(
        rows,
        base_schema=base_schema,
        endpoint_snapshots=endpoint_snapshots,
        dialect=dialect,
        max_characters=max_characters,
        max_schema_characters=max_schema_characters,
    )
    train, validation, test = split_private_examples(
        examples, validation_percent=validation_percent, test_percent=test_percent
    )
    if not train or not validation or not test:
        raise ValueError("A divisão gerou uma partição vazia; aumente a fonte ou ajuste os percentuais.")

    safe_label = re.sub(r"[^a-zA-Z0-9._-]+", "-", output_label).strip("-_")
    if not safe_label:
        raise ValueError("output_label deve conter letras, números, ponto, hífen ou sublinhado.")
    output = root_dir / "data" / "processed" / "phase-02" / f"{safe_label}-{fingerprint(base_schema)[:12]}"
    if output.exists():
        raise FileExistsError(f"A saída já existe: {output}. Escolha outro output_label.")
    output.mkdir(parents=True)
    write_jsonl(output / "train.jsonl", train)
    write_jsonl(output / "validation.jsonl", validation)
    write_jsonl(output / "test.jsonl", test)

    report = PrivatePreparationReport(
        created_at_utc=datetime.now(UTC).isoformat(),
        source_rows=len(rows),
        accepted_rows=len(examples),
        train_rows=len(train),
        validation_rows=len(validation),
        test_rows=len(test),
        schema_snapshots=1 + len(endpoint_snapshots or {}),
        dynamic_endpoint_rows=dynamic_endpoint_rows,
        dialect=dialect,
        split_strategy="deterministic_record_hash; schema snapshot repeated only as runtime context",
        rejected=dict(sorted(rejected.items())),
        queries_path=_display_path(queries_path, root_dir),
        base_schema_path=_display_path(base_schema_path, root_dir),
        endpoint_manifest_path=_display_path(endpoint_manifest_path, root_dir) if endpoint_manifest_path else None,
        processed_path=_display_path(output, root_dir),
    )
    reports = root_dir / "artifacts" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    with (reports / f"phase-02-intake-{safe_label}.json").open("x", encoding="utf-8", newline="\n") as output_file:
        json.dump(asdict(report), output_file, ensure_ascii=False, indent=2, sort_keys=True)
        output_file.write("\n")
    return report

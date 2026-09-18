"""Contratos determinísticos para a geração criativa por estágios."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from llm_to_sql.evaluation import normalize_model_output


EXPECTED_STYLES = ("direta", "analitica", "conversacional", "concisa")
_TECHNICAL = re.compile(r"\b(select|from|where|sql|schema|tabela|coluna|column|group by|order by)\b", re.IGNORECASE)


@dataclass(frozen=True)
class QuestionCandidate:
    identifier: str
    style: str
    question: str


def parse_json_response(response: str) -> dict[str, Any]:
    normalized = normalize_model_output(response).strip()
    normalized = re.sub(r"^```(?:json)?\s*", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s*```$", "", normalized)
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as error:
        raise ValueError("Resposta não contém JSON válido.") from error
    if not isinstance(payload, dict):
        raise ValueError("Resposta JSON deve ser um objeto.")
    return payload


def validate_writer_response(response: str, semantic_brief: dict[str, Any]) -> tuple[QuestionCandidate, ...]:
    payload = parse_json_response(response)
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or len(raw_candidates) != len(EXPECTED_STYLES):
        raise ValueError("O writer deve retornar exatamente quatro candidatos.")
    candidates: list[QuestionCandidate] = []
    identifiers: set[str] = set()
    styles: set[str] = set()
    literal_values = [str(value) for value in semantic_brief.get("literal_values", ()) if value is not None]
    for item in raw_candidates:
        if not isinstance(item, dict):
            raise ValueError("Candidato deve ser um objeto JSON.")
        identifier = str(item.get("id", "")).strip()
        style = str(item.get("style", "")).strip().casefold()
        question = " ".join(str(item.get("question", "")).split())
        if not identifier or identifier in identifiers:
            raise ValueError("IDs de candidatos devem ser únicos e não vazios.")
        if style not in EXPECTED_STYLES or style in styles:
            raise ValueError("Os quatro estilos obrigatórios devem aparecer uma vez.")
        if len(question) < 12 or len(question) > 320 or not question.endswith("?"):
            raise ValueError("Pergunta deve ser natural, limitada e terminar com interrogação.")
        if _TECHNICAL.search(question):
            raise ValueError("Pergunta expõe vocabulário técnico proibido.")
        folded = question.casefold()
        for literal in literal_values:
            if literal.casefold() not in folded:
                raise ValueError(f"Pergunta não preserva o literal obrigatório: {literal}")
        _validate_aggregation_language(question, str(semantic_brief.get("aggregation", "none")))
        identifiers.add(identifier)
        styles.add(style)
        candidates.append(QuestionCandidate(identifier, style, question))
    return tuple(candidates)


def validate_critic_response(response: str, allowed_ids: set[str]) -> dict[str, Any]:
    payload = parse_json_response(response)
    selected = str(payload.get("selected_id", "")).strip()
    if selected not in allowed_ids:
        raise ValueError("Crítico selecionou candidato inexistente ou reprovado.")
    for key in ("semantic_fidelity", "naturalness", "clarity"):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
            raise ValueError(f"Nota inválida: {key}.")
    reason = str(payload.get("reason", "")).strip()
    if not reason or len(reason) > 500:
        raise ValueError("Justificativa do crítico inválida.")
    return payload


def _validate_aggregation_language(question: str, aggregation: str) -> None:
    folded = question.casefold()
    required = {
        "COUNT": ("quant", "número", "numero"),
        "SUM": ("total", "soma"),
        "AVG": ("média", "media"),
        "MAX": ("maior", "máxim", "maxim"),
        "MIN": ("menor", "mínim", "minim"),
    }.get(aggregation.upper())
    if required and not any(token in folded for token in required):
        raise ValueError(f"Pergunta não expressa a agregação {aggregation}.")

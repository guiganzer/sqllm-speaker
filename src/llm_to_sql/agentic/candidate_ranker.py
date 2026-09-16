"""Ranking determinístico de candidatos SQL por aderência semântica à pergunta."""

from __future__ import annotations

from dataclasses import dataclass
import re

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


@dataclass(frozen=True)
class RankedCandidate:
    sql: str
    score: int
    reasons: tuple[str, ...]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def score_candidate(question: str, sql: str) -> RankedCandidate:
    normalized = " ".join(question.lower().split())
    reasons: list[str] = []
    score = 0
    try:
        tree = parse_one(sql, read="postgres")
    except ParseError:
        return RankedCandidate(sql, -100, ("parse inválido",))

    aggregate_names = {type(node).__name__.lower() for node in tree.find_all(exp.AggFunc)}
    if _contains_any(normalized, ("quantos", "quantas", "quantidade", "conte")):
        delta = 5 if "count" in aggregate_names else -5
        score += delta
        reasons.append("COUNT coerente" if delta > 0 else "COUNT ausente")
    if _contains_any(normalized, ("média", "medio", "médio", "media")):
        delta = 5 if "avg" in aggregate_names else -5
        score += delta
        reasons.append("AVG coerente" if delta > 0 else "AVG ausente")
    if _contains_any(normalized, ("soma", "some", "total pago", "vendas", "receita")):
        delta = 4 if "sum" in aggregate_names else -4
        score += delta
        reasons.append("SUM coerente" if delta > 0 else "SUM ausente")

    group = tree.find(exp.Group)
    grouped_cue = bool(re.search(r"\b(por|cada)\s+(categoria|cliente|funcion[aá]rio|loja|dia|m[eê]s|pa[ií]s)", normalized))
    if grouped_cue:
        delta = 3 if group is not None else -3
        score += delta
        reasons.append("GROUP BY coerente" if delta > 0 else "GROUP BY ausente")

    requested_limit = re.search(r"\b(?:os|as|até|primeir[oa]s?)\s+(\d+)\b", normalized)
    limit = tree.find(exp.Limit)
    if requested_limit:
        actual = limit.expression.name if limit is not None and limit.expression is not None else None
        delta = 4 if actual == requested_limit.group(1) else -4
        score += delta
        reasons.append("LIMIT coerente" if delta > 0 else "LIMIT divergente")

    order = tree.find(exp.Order)
    order_sql = order.sql(dialect="postgres").lower() if order is not None else ""
    if _contains_any(normalized, ("maior", "maiores", "que mais", "mais vendidos", "mais pagaram", "das maiores")):
        delta = 2 if " desc" in order_sql else -2
        score += delta
        reasons.append("ordem DESC coerente" if delta > 0 else "ordem DESC ausente")
    if _contains_any(normalized, ("menor", "menores", "que menos", "menos vendidos", "menos pagaram")):
        delta = 2 if order is not None and " desc" not in order_sql else -2
        score += delta
        reasons.append("ordem ASC coerente" if delta > 0 else "ordem ASC ausente")

    if _contains_any(normalized, ("por mês", "por mes", "mensal")):
        temporal_sql = tree.sql(dialect="postgres").lower()
        delta = 3 if "extract(month" in temporal_sql or "date_trunc('month'" in temporal_sql else -3
        score += delta
        reasons.append("agrupamento mensal coerente" if delta > 0 else "agrupamento mensal ausente")
    return RankedCandidate(sql, score, tuple(reasons))


def rank_candidates(question: str, candidates: list[str]) -> list[RankedCandidate]:
    if not candidates:
        raise ValueError("É necessário ao menos um candidato.")
    return sorted((score_candidate(question, sql) for sql in candidates), key=lambda item: item.score, reverse=True)

"""Contratos do corpus público de especialização Pagila (fase 2)."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from sqlglot import parse_one


SYSTEM_PROMPT = (
    "Você é um assistente especializado em SQL. Gere somente uma consulta SQL "
    "compatível com o schema fornecido. Não explique a resposta."
)


@dataclass(frozen=True)
class SpecializationSpec:
    """Um exemplo gerado por família, antes de receber o contexto de schema."""

    identifier: str
    family: str
    question: str
    sql: str


def _specs_for_values(family: str, question_template: str, sql_template: str, values: Iterable[object]) -> list[SpecializationSpec]:
    rows: list[SpecializationSpec] = []
    for position, value in enumerate(values, start=1):
        rows.append(SpecializationSpec(f"{family}-{position:02d}", family, question_template.format(value=value), sql_template.format(value=value)))
    return rows


def build_specs() -> list[SpecializationSpec]:
    """Gera intenções públicas parametrizadas distintas dos benchmarks congelados."""

    specs: list[SpecializationSpec] = []
    specs += _specs_for_values(
        "film-rating-length",
        "Quantos filmes com classificação {value[0]} duram mais de {value[1]} minutos?",
        "SELECT COUNT(*) AS total_filmes FROM film WHERE rating = '{value[0]}' AND length > {value[1]}",
        [(rating, length) for rating in ("G", "PG", "PG-13", "R", "NC-17") for length in (80, 120, 160)],
    )
    specs += _specs_for_values(
        "film-rating-cost",
        "Liste os títulos de filmes {value[0]} cujo custo de reposição seja maior que {value[1]}.",
        "SELECT title, replacement_cost FROM film WHERE rating = '{value[0]}' AND replacement_cost > {value[1]} ORDER BY replacement_cost DESC, title",
        [(rating, cost) for rating in ("G", "PG", "PG-13", "R", "NC-17") for cost in (15, 25)],
    )
    specs += _specs_for_values(
        "film-title-prefix",
        "Quais filmes têm título iniciado pela letra {value}?",
        "SELECT title, release_year FROM film WHERE title ILIKE '{value}%' ORDER BY title",
        list("ABCDEFGHJKLMNPRST"),
    )
    specs += _specs_for_values(
        "film-rental-period",
        "Quais filmes têm período de locação igual a {value} dias?",
        "SELECT title, rental_duration FROM film WHERE rental_duration = {value} ORDER BY title",
        range(3, 8),
    )
    specs += _specs_for_values(
        "film-special-feature",
        "Quantos filmes oferecem o recurso especial {value}?",
        "SELECT COUNT(*) AS total_filmes FROM film WHERE special_features @> ARRAY['{value}']",
        ["Trailers", "Commentaries", "Deleted Scenes", "Behind the Scenes"],
    )
    specs += _specs_for_values(
        "category-rating",
        "Quais filmes da categoria {value[0]} possuem classificação {value[1]}?",
        "SELECT film.title FROM category JOIN film_category USING (category_id) JOIN film USING (film_id) WHERE category.name = '{value[0]}' AND film.rating = '{value[1]}' ORDER BY film.title",
        [(category, rating) for category in ("Action", "Comedy", "Drama", "Family", "Horror", "Sports") for rating in ("PG", "R")],
    )
    specs += _specs_for_values(
        "category-long-film",
        "Liste os filmes de {value[0]} com mais de {value[1]} minutos.",
        "SELECT film.title, film.length FROM category JOIN film_category USING (category_id) JOIN film USING (film_id) WHERE category.name = '{value[0]}' AND film.length > {value[1]} ORDER BY film.length DESC, film.title",
        [(category, length) for category in ("Action", "Animation", "Children", "Classics", "Documentary", "Music") for length in (100, 150)],
    )
    specs += _specs_for_values(
        "actor-letter",
        "Quais atores têm primeiro nome iniciado pela letra {value}?",
        "SELECT first_name, last_name FROM actor WHERE first_name ILIKE '{value}%' ORDER BY last_name, first_name",
        list("ABCDEFGHJKLMNPRST"),
    )
    specs += _specs_for_values(
        "actor-film-rating",
        "Quais atores participaram de filmes com classificação {value}?",
        "SELECT DISTINCT actor.first_name, actor.last_name FROM actor JOIN film_actor USING (actor_id) JOIN film USING (film_id) WHERE film.rating = '{value}' ORDER BY actor.last_name, actor.first_name",
        ("G", "PG", "PG-13", "R", "NC-17"),
    )
    specs += _specs_for_values(
        "customer-letter",
        "Quais clientes têm sobrenome iniciado pela letra {value}?",
        "SELECT first_name, last_name, email FROM customer WHERE last_name ILIKE '{value}%' ORDER BY last_name, first_name",
        list("ABCDEFGHJKLMNPRST"),
    )
    specs += _specs_for_values(
        "customer-store-active",
        "Quantos clientes ativos existem na loja {value}?",
        "SELECT COUNT(*) AS total_clientes_ativos FROM customer WHERE store_id = {value} AND active = 1",
        (1, 2),
    )
    specs += _specs_for_values(
        "address-district",
        "Quais clientes moram no distrito {value}?",
        "SELECT customer.first_name, customer.last_name FROM customer JOIN address USING (address_id) WHERE address.district = '{value}' ORDER BY customer.last_name, customer.first_name",
        ("California", "Texas", "Maharashtra", "Ontario", "Hessen", "West Java"),
    )
    specs += _specs_for_values(
        "inventory-film-copy",
        "Em quais lojas há cópias do filme de identificador {value}?",
        "SELECT store_id, COUNT(*) AS copias FROM inventory WHERE film_id = {value} GROUP BY store_id ORDER BY store_id",
        (1, 10, 25, 50, 100, 250, 500, 750, 1000),
    )
    specs += _specs_for_values(
        "rental-duration",
        "Quais locações duraram mais de {value} dias?",
        "SELECT rental_id, customer_id, LOWER(rental_period) AS retirada, UPPER(rental_period) AS devolucao FROM rental WHERE UPPER(rental_period) - LOWER(rental_period) > INTERVAL '{value} days' ORDER BY rental_id",
        (1, 2, 3, 4, 5, 6, 7),
    )
    specs += _specs_for_values(
        "payment-amount-bands",
        "Quantos pagamentos foram maiores que {value}?",
        "SELECT COUNT(*) AS total_pagamentos FROM payment WHERE amount > {value}",
        (1, 3, 5, 7, 9, 11),
    )
    specs += _specs_for_values(
        "payment-customer-threshold",
        "Quais clientes fizeram pagamentos acima de {value}?",
        "SELECT DISTINCT customer.first_name, customer.last_name FROM customer JOIN payment USING (customer_id) WHERE payment.amount > {value} ORDER BY customer.last_name, customer.first_name",
        (2, 4, 6, 8, 10),
    )
    _validate_specs(specs)
    return specs


def _validate_specs(specs: Iterable[SpecializationSpec]) -> None:
    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    seen_sql: set[str] = set()
    for spec in specs:
        if spec.identifier in seen_ids:
            raise ValueError(f"Identificador repetido: {spec.identifier}")
        seen_ids.add(spec.identifier)
        normalized_question = " ".join(spec.question.lower().split())
        if normalized_question in seen_questions:
            raise ValueError(f"Pergunta repetida: {spec.identifier}")
        seen_questions.add(normalized_question)
        normalized_sql = canonical_sql(spec.sql)
        if normalized_sql in seen_sql:
            raise ValueError(f"SQL repetido: {spec.identifier}")
        seen_sql.add(normalized_sql)


def canonical_sql(sql: str) -> str:
    return parse_one(sql, read="postgres").sql(dialect="postgres", pretty=False)


def corpus_fingerprint(specs: Iterable[SpecializationSpec]) -> str:
    content = "\n".join(f"{spec.identifier}\t{spec.question}\t{canonical_sql(spec.sql)}" for spec in specs)
    return sha256(content.encode("utf-8")).hexdigest()

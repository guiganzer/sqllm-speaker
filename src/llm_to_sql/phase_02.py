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


def build_specs(edition: str = "v1") -> list[SpecializationSpec]:
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
    if edition == "v2":
        specs.extend(_v2_specs())
    elif edition != "v1":
        raise ValueError("edition deve ser v1 ou v2.")
    _validate_specs(specs)
    return specs


def _v2_specs() -> list[SpecializationSpec]:
    """Famílias relacionais adicionais para a segunda iteração Pagila."""

    specs: list[SpecializationSpec] = []
    specs += _specs_for_values(
        "staff-payment-left",
        "Para cada funcionário, mostre a quantidade de pagamentos de valor até {value}, incluindo funcionários sem pagamento.",
        "SELECT staff.staff_id, staff.first_name, staff.last_name, COUNT(payment.payment_id) AS total_pagamentos FROM staff LEFT JOIN payment ON payment.staff_id = staff.staff_id AND payment.amount <= {value} GROUP BY staff.staff_id, staff.first_name, staff.last_name ORDER BY total_pagamentos DESC, staff.last_name, staff.first_name",
        (2, 4, 6, 8, 10, 12),
    )
    specs += _specs_for_values(
        "customer-rental-left",
        "Para cada cliente da loja {value}, informe o número de locações, incluindo quem não alugou.",
        "SELECT customer.customer_id, customer.first_name, customer.last_name, COUNT(rental.rental_id) AS total_locacoes FROM customer LEFT JOIN rental ON rental.customer_id = customer.customer_id WHERE customer.store_id = {value} GROUP BY customer.customer_id, customer.first_name, customer.last_name ORDER BY total_locacoes DESC, customer.last_name, customer.first_name",
        (1, 2),
    )
    specs += _specs_for_values(
        "actor-category-membership",
        "Quais atores participaram de filmes da categoria {value}?",
        "SELECT DISTINCT actor.first_name, actor.last_name FROM actor JOIN film_actor ON film_actor.actor_id = actor.actor_id JOIN film_category ON film_category.film_id = film_actor.film_id JOIN category ON category.category_id = film_category.category_id WHERE category.name = '{value}' ORDER BY actor.last_name, actor.first_name",
        ("Action", "Animation", "Comedy", "Documentary", "Family", "Horror", "Music", "Sports"),
    )
    specs += _specs_for_values(
        "inventory-store-rating",
        "Quantas cópias de filmes com classificação {value[0]} existem na loja {value[1]}?",
        "SELECT inventory.store_id, COUNT(inventory.inventory_id) AS total_copias FROM inventory JOIN film ON film.film_id = inventory.film_id WHERE film.rating = '{value[0]}' AND inventory.store_id = {value[1]} GROUP BY inventory.store_id ORDER BY inventory.store_id",
        [(rating, store) for rating in ("G", "PG", "PG-13", "R", "NC-17") for store in (1, 2)],
    )
    specs += _specs_for_values(
        "staff-payment-range",
        "Qual é o total de pagamentos entre {value[0]} e {value[1]} por funcionário?",
        "SELECT staff.staff_id, staff.first_name, staff.last_name, ROUND(SUM(payment.amount), 2) AS total_pagamentos FROM staff JOIN payment ON payment.staff_id = staff.staff_id WHERE payment.amount BETWEEN {value[0]} AND {value[1]} GROUP BY staff.staff_id, staff.first_name, staff.last_name ORDER BY total_pagamentos DESC, staff.last_name, staff.first_name",
        ((0, 3), (3, 6), (6, 9), (9, 12)),
    )
    specs += _specs_for_values(
        "city-active-customer",
        "Quais cidades têm clientes ativos e quantos são, para países iniciados por {value}?",
        "SELECT city.city, COUNT(customer.customer_id) AS total_clientes_ativos FROM country JOIN city ON city.country_id = country.country_id JOIN address ON address.city_id = city.city_id JOIN customer ON customer.address_id = address.address_id WHERE country.country ILIKE '{value}%' AND customer.active = 1 GROUP BY city.city ORDER BY total_clientes_ativos DESC, city.city",
        ("A", "B", "C", "D", "E", "F", "G", "I"),
    )
    specs += _specs_for_values(
        "rental-by-day",
        "Quantas locações foram iniciadas no dia {value} do mês?",
        "SELECT DATE(LOWER(rental_period)) AS dia, COUNT(*) AS total_locacoes FROM rental WHERE EXTRACT(DAY FROM LOWER(rental_period)) = {value} GROUP BY DATE(LOWER(rental_period)) ORDER BY dia",
        (1, 5, 10, 15, 20, 25, 30),
    )
    specs += _specs_for_values(
        "film-description-order",
        "Liste os {value} filmes com descrições mais longas entre os de classificação PG.",
        "SELECT title, LENGTH(description) AS tamanho_descricao FROM film WHERE rating = 'PG' AND description IS NOT NULL ORDER BY tamanho_descricao DESC, title LIMIT {value}",
        (3, 5, 8, 10),
    )
    specs += _specs_for_values(
        "customer-list-country-view",
        "Quais {value} clientes da view de clientes pertencem a países iniciados por A?",
        "SELECT id, name, country FROM customer_list WHERE country ILIKE 'A%' ORDER BY name LIMIT {value}",
        (3, 5, 8, 10),
    )
    specs += _specs_for_values(
        "sales-category-view",
        "Quais categorias da view de vendas por filme têm vendas totais acima de {value}?",
        "SELECT category, total_sales FROM sales_by_film_category WHERE total_sales > {value} ORDER BY total_sales DESC, category",
        (100, 300, 500, 700, 900),
    )
    specs += _specs_for_values(
        "film-actor-alias",
        "Quais títulos de filmes com classificação {value} têm atores cujo sobrenome começa por S?",
        "SELECT DISTINCT f.title FROM film AS f JOIN film_actor AS fa ON fa.film_id = f.film_id JOIN actor AS a ON a.actor_id = fa.actor_id WHERE f.rating = '{value}' AND a.last_name ILIKE 'S%' ORDER BY f.title",
        ("G", "PG", "PG-13", "R", "NC-17"),
    )
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

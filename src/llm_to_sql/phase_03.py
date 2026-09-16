"""Corpus Pagila v3: variações PT-BR parametrizadas com cobertura semântica ampla."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .phase_02 import SpecializationSpec


def _render(
    family: str,
    rows: Iterable[Mapping[str, object]],
    questions: tuple[str, ...],
    sql: str,
) -> list[SpecializationSpec]:
    specs: list[SpecializationSpec] = []
    for row_number, values in enumerate(rows, start=1):
        rendered_sql = sql.format_map(values)
        for paraphrase_number, template in enumerate(questions, start=1):
            identifier = f"{family}-{row_number:03d}-p{paraphrase_number}"
            specs.append(
                SpecializationSpec(
                    identifier,
                    family,
                    template.format_map(values),
                    rendered_sql,
                )
            )
    return specs


def build_v3_specs() -> list[SpecializationSpec]:
    """Gera cerca de dois mil exemplos; famílias inteiras ficam fora do treino."""

    ratings = ("G", "PG", "PG-13", "R", "NC-17")
    categories = (
        "Action", "Animation", "Children", "Classics", "Comedy", "Documentary",
        "Drama", "Family", "Foreign", "Games", "Horror", "Music", "New",
        "Sci-Fi", "Sports", "Travel",
    )
    prefixes = tuple("ABCDEFGHJKLMNPRST")
    specs: list[SpecializationSpec] = []

    specs += _render(
        "v3-film-rating-length",
        ({"rating": rating, "length": length} for rating in ratings for length in range(70, 181, 15)),
        (
            "Quantos filmes {rating} têm duração superior a {length} minutos?",
            "Conte os filmes classificados como {rating} com mais de {length} minutos.",
            "Qual é o total de filmes de classificação {rating} cuja duração passa de {length} minutos?",
            "Informe a quantidade de filmes {rating} acima de {length} minutos.",
        ),
        "SELECT COUNT(*) AS total_filmes FROM film WHERE rating = '{rating}' AND length > {length}",
    )
    specs += _render(
        "v3-film-rating-cost",
        ({"rating": rating, "cost": cost} for rating in ratings for cost in range(10, 31, 4)),
        (
            "Liste os filmes {rating} com custo de reposição acima de {cost}.",
            "Quais títulos classificados como {rating} custam mais de {cost} para reposição?",
            "Mostre título e custo dos filmes {rating} cujo replacement cost supera {cost}.",
        ),
        "SELECT title, replacement_cost FROM film WHERE rating = '{rating}' AND replacement_cost > {cost} ORDER BY replacement_cost DESC, title",
    )
    specs += _render(
        "v3-category-rating",
        ({"category": category, "rating": rating} for category in categories for rating in ratings),
        (
            "Quais filmes de {category} têm classificação {rating}?",
            "Liste os títulos da categoria {category} classificados como {rating}.",
            "Mostre filmes {rating} pertencentes à categoria {category}.",
        ),
        "SELECT film.title FROM category JOIN film_category ON film_category.category_id = category.category_id JOIN film ON film.film_id = film_category.film_id WHERE category.name = '{category}' AND film.rating = '{rating}' ORDER BY film.title",
    )
    specs += _render(
        "v3-category-length",
        ({"category": category, "length": length} for category in categories for length in (80, 100, 120, 140, 160)),
        (
            "Liste filmes de {category} com mais de {length} minutos.",
            "Quais títulos da categoria {category} ultrapassam {length} minutos?",
            "Mostre título e duração dos filmes de {category} acima de {length} minutos.",
        ),
        "SELECT film.title, film.length FROM category JOIN film_category ON film_category.category_id = category.category_id JOIN film ON film.film_id = film_category.film_id WHERE category.name = '{category}' AND film.length > {length} ORDER BY film.length DESC, film.title",
    )
    specs += _render(
        "v3-actor-prefix-rating",
        ({"prefix": prefix, "rating": rating} for prefix in prefixes for rating in ratings),
        (
            "Quais atores de sobrenome iniciado por {prefix} atuaram em filmes {rating}?",
            "Liste atores cujo sobrenome começa com {prefix} e que aparecem em filmes {rating}.",
            "Mostre os atores com last name começando em {prefix} presentes em títulos {rating}.",
        ),
        "SELECT DISTINCT actor.first_name, actor.last_name FROM actor JOIN film_actor ON film_actor.actor_id = actor.actor_id JOIN film ON film.film_id = film_actor.film_id WHERE actor.last_name ILIKE '{prefix}%' AND film.rating = '{rating}' ORDER BY actor.last_name, actor.first_name",
    )
    specs += _render(
        "v3-customer-country-active",
        ({"prefix": prefix, "active": active} for prefix in prefixes for active in (0, 1)),
        (
            "Quantos clientes com status ativo igual a {active} moram em países iniciados por {prefix}?",
            "Conte clientes com active = {active} em países cujo nome começa com {prefix}.",
            "Qual o total de clientes de países com inicial {prefix} e indicador ativo {active}?",
        ),
        "SELECT COUNT(*) AS total_clientes FROM customer JOIN address ON address.address_id = customer.address_id JOIN city ON city.city_id = address.city_id JOIN country ON country.country_id = city.country_id WHERE customer.active = {active} AND country.country ILIKE '{prefix}%'",
    )
    specs += _render(
        "v3-inventory-store-rating",
        ({"store": store, "rating": rating, "cost": cost} for store in (1, 2) for rating in ratings for cost in (10, 15, 20, 25)),
        (
            "Quantas cópias na loja {store} são de filmes {rating} com reposição acima de {cost}?",
            "Conte o estoque da loja {store} de títulos {rating} cujo custo de reposição supera {cost}.",
            "Informe a quantidade de exemplares na loja {store}, classificação {rating}, replacement cost maior que {cost}.",
        ),
        "SELECT COUNT(inventory.inventory_id) AS total_copias FROM inventory JOIN film ON film.film_id = inventory.film_id WHERE inventory.store_id = {store} AND film.rating = '{rating}' AND film.replacement_cost > {cost}",
    )
    specs += _render(
        "v3-staff-payment-range",
        ({"low": low, "high": low + 3} for low in range(0, 10)),
        (
            "Qual o valor total de pagamentos entre {low} e {high} por funcionário?",
            "Some por funcionário os pagamentos de {low} até {high}.",
            "Mostre cada funcionário e a soma recebida na faixa de {low} a {high}.",
            "Agrupe por funcionário o total pago entre {low} e {high}.",
        ),
        "SELECT staff.staff_id, staff.first_name, staff.last_name, ROUND(SUM(payment.amount), 2) AS total_pagamentos FROM staff JOIN payment ON payment.staff_id = staff.staff_id WHERE payment.amount BETWEEN {low} AND {high} GROUP BY staff.staff_id, staff.first_name, staff.last_name ORDER BY total_pagamentos DESC, staff.last_name, staff.first_name",
    )
    specs += _render(
        "v3-customer-payment-top",
        ({"amount": amount, "limit": limit} for amount in (2, 4, 6, 8, 10) for limit in (3, 5, 10, 15)),
        (
            "Quais são os {limit} clientes com maior total de pagamentos acima de {amount}?",
            "Liste os {limit} maiores pagadores considerando pagamentos superiores a {amount}.",
            "Mostre nome e soma dos {limit} clientes que mais pagaram em valores acima de {amount}.",
        ),
        "SELECT customer.customer_id, customer.first_name, customer.last_name, ROUND(SUM(payment.amount), 2) AS total_pago FROM customer JOIN payment ON payment.customer_id = customer.customer_id WHERE payment.amount > {amount} GROUP BY customer.customer_id, customer.first_name, customer.last_name ORDER BY total_pago DESC, customer.last_name, customer.first_name LIMIT {limit}",
    )
    specs += _render(
        "v3-rental-day-store",
        ({"day": day, "store": store} for day in range(1, 29) for store in (1, 2)),
        (
            "Quantas locações da loja {store} começaram no dia {day} do mês?",
            "Conte as retiradas iniciadas no dia {day} para o estoque da loja {store}.",
            "Informe o total de locações iniciadas no dia mensal {day} na loja {store}.",
        ),
        "SELECT COUNT(DISTINCT rental.rental_id) AS total_locacoes FROM rental JOIN inventory ON inventory.inventory_id = rental.inventory_id WHERE inventory.store_id = {store} AND EXTRACT(DAY FROM LOWER(rental.rental_period)) = {day}",
    )
    specs += _render(
        "v3-category-revenue-top",
        ({"amount": amount, "limit": limit} for amount in (100, 300, 500, 700) for limit in (3, 5, 8, 10)),
        (
            "Quais as {limit} categorias com vendas acima de {amount}?",
            "Liste até {limit} categorias cuja venda total supera {amount}, das maiores para as menores.",
            "Mostre as {limit} categorias mais vendidas entre as que passaram de {amount}.",
            "Na view de vendas por categoria, retorne as {limit} primeiras acima de {amount}.",
        ),
        "SELECT category, total_sales FROM sales_by_film_category WHERE total_sales > {amount} ORDER BY total_sales DESC, category LIMIT {limit}",
    )
    specs += _render(
        "v3-description-top",
        ({"rating": rating, "limit": limit} for rating in ratings for limit in (3, 5, 8, 10, 15)),
        (
            "Liste os {limit} filmes {rating} com descrições mais longas.",
            "Quais são os {limit} títulos {rating} de maior descrição?",
            "Mostre os {limit} filmes classificados como {rating} ordenados pelo tamanho da descrição.",
        ),
        "SELECT title, LENGTH(description) AS tamanho_descricao FROM film WHERE rating = '{rating}' AND description IS NOT NULL ORDER BY tamanho_descricao DESC, title LIMIT {limit}",
    )
    specs += _render(
        "v3-category-cost",
        ({"category": category, "cost": cost} for category in categories for cost in (10, 15, 20, 25, 30)),
        (
            "Quantos filmes de {category} têm custo de reposição acima de {cost}?",
            "Conte os títulos da categoria {category} cujo replacement cost supera {cost}.",
            "Qual é a quantidade de filmes em {category} com reposição maior que {cost}?",
        ),
        "SELECT COUNT(*) AS total_filmes FROM category JOIN film_category ON film_category.category_id = category.category_id JOIN film ON film.film_id = film_category.film_id WHERE category.name = '{category}' AND film.replacement_cost > {cost}",
    )
    return specs

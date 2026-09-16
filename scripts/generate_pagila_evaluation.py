"""Gera e executa uma avaliação pública de leitura para o banco Pagila local."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_to_sql.agentic.policy import ReadOnlySqlPolicy
from sqlglot import parse_one
from sqlglot.errors import ParseError


@dataclass(frozen=True)
class EvaluationSpec:
    identifier: str
    category: str
    question: str
    sql: str


def build_specs() -> list[EvaluationSpec]:
    """Retorna intenções públicas programáticas; não são exemplos de treino curados."""

    rows = [
        ("film-count", "filmes", "Quantos filmes existem no catálogo?", "SELECT COUNT(*) AS total_filmes FROM film"),
        ("described-film-count", "descricoes", "Quantos filmes possuem descrição?", "SELECT COUNT(*) AS filmes_com_descricao FROM film WHERE description IS NOT NULL AND description <> ''"),
        ("film-rating-count", "agregacao", "Quantos filmes existem por classificação indicativa?", "SELECT rating, COUNT(*) AS total_filmes FROM film GROUP BY rating ORDER BY total_filmes DESC, rating"),
        ("category-film-count", "join", "Quantos filmes existem por categoria?", "SELECT category.name AS categoria, COUNT(film_category.film_id) AS total_filmes FROM category JOIN film_category USING (category_id) GROUP BY category.name ORDER BY total_filmes DESC, categoria"),
        ("category-average-length", "join", "Qual é a duração média dos filmes por categoria?", "SELECT category.name AS categoria, ROUND(AVG(film.length), 2) AS duracao_media FROM category JOIN film_category USING (category_id) JOIN film USING (film_id) GROUP BY category.name ORDER BY duracao_media DESC, categoria"),
        ("language-film-count", "join", "Quantos filmes existem por idioma?", "SELECT language.name AS idioma, COUNT(film.film_id) AS total_filmes FROM language LEFT JOIN film USING (language_id) GROUP BY language.name ORDER BY total_filmes DESC, idioma"),
        ("actor-film-count", "join", "Quais atores participam de mais filmes?", "SELECT actor.first_name, actor.last_name, COUNT(film_actor.film_id) AS total_filmes FROM actor JOIN film_actor USING (actor_id) GROUP BY actor.actor_id, actor.first_name, actor.last_name ORDER BY total_filmes DESC, actor.last_name, actor.first_name LIMIT 20"),
        ("country-city-count", "join", "Quantas cidades existem por país?", "SELECT country.country, COUNT(city.city_id) AS total_cidades FROM country LEFT JOIN city USING (country_id) GROUP BY country.country ORDER BY total_cidades DESC, country.country"),
        ("customers-by-store", "join", "Quantos clientes existem por loja?", "SELECT store.store_id, COUNT(customer.customer_id) AS total_clientes FROM store LEFT JOIN customer USING (store_id) GROUP BY store.store_id ORDER BY store.store_id"),
        ("staff-by-store", "join", "Quantos funcionários trabalham em cada loja?", "SELECT store.store_id, COUNT(staff.staff_id) AS total_funcionarios FROM store LEFT JOIN staff USING (store_id) GROUP BY store.store_id ORDER BY store.store_id"),
        ("rental-by-month", "tempo", "Quantas locações foram feitas por mês?", "SELECT DATE_TRUNC('month', LOWER(rental_period)) AS mes, COUNT(*) AS total_locacoes FROM rental GROUP BY mes ORDER BY mes"),
        ("payment-by-staff", "agregacao", "Qual o total de pagamentos processado por funcionário?", "SELECT staff.staff_id, ROUND(SUM(payment.amount), 2) AS total_pagamentos FROM staff JOIN payment USING (staff_id) GROUP BY staff.staff_id ORDER BY total_pagamentos DESC, staff.staff_id"),
        ("payment-by-store", "join", "Qual o total de pagamentos por loja?", "SELECT store.store_id, ROUND(SUM(payment.amount), 2) AS total_pagamentos FROM store JOIN staff USING (store_id) JOIN payment USING (staff_id) GROUP BY store.store_id ORDER BY store.store_id"),
        ("top-customers-payments", "join", "Quais clientes realizaram mais pagamentos?", "SELECT customer.first_name, customer.last_name, ROUND(SUM(payment.amount), 2) AS total_pago FROM customer JOIN payment USING (customer_id) GROUP BY customer.customer_id, customer.first_name, customer.last_name ORDER BY total_pago DESC, customer.last_name, customer.first_name LIMIT 20"),
        ("top-rented-films", "join", "Quais filmes foram mais alugados?", "SELECT film.title, COUNT(rental.rental_id) AS total_locacoes FROM film JOIN inventory USING (film_id) JOIN rental USING (inventory_id) GROUP BY film.film_id, film.title ORDER BY total_locacoes DESC, film.title LIMIT 20"),
        ("inventory-by-store", "join", "Quantos itens de estoque cada loja possui?", "SELECT store.store_id, COUNT(inventory.inventory_id) AS total_itens FROM store LEFT JOIN inventory USING (store_id) GROUP BY store.store_id ORDER BY store.store_id"),
        ("description-length-by-rating", "descricoes", "Qual o tamanho médio das descrições por classificação indicativa?", "SELECT rating, ROUND(AVG(LENGTH(description)), 2) AS tamanho_medio_descricao FROM film GROUP BY rating ORDER BY tamanho_medio_descricao DESC, rating"),
        ("film-cost-by-rating", "agregacao", "Qual o custo médio de reposição por classificação indicativa?", "SELECT rating, ROUND(AVG(replacement_cost), 2) AS custo_medio_reposicao FROM film GROUP BY rating ORDER BY custo_medio_reposicao DESC, rating"),
        ("rental-duration-by-category", "join", "Qual a duração média de locação por categoria?", "SELECT category.name AS categoria, ROUND(AVG(film.rental_duration), 2) AS duracao_media_locacao FROM category JOIN film_category USING (category_id) JOIN film USING (film_id) GROUP BY category.name ORDER BY duracao_media_locacao DESC, categoria"),
        ("active-customers", "filtro", "Quantos clientes ativos e inativos existem?", "SELECT active, COUNT(*) AS total_clientes FROM customer GROUP BY active ORDER BY active DESC"),
        ("cities-with-customers", "join", "Quais cidades possuem mais clientes?", "SELECT city.city, COUNT(customer.customer_id) AS total_clientes FROM city JOIN address USING (city_id) JOIN customer USING (address_id) GROUP BY city.city ORDER BY total_clientes DESC, city.city LIMIT 20"),
        ("category-revenue", "join", "Qual a receita total por categoria de filme?", "SELECT category.name AS categoria, ROUND(SUM(payment.amount), 2) AS receita_total FROM category JOIN film_category USING (category_id) JOIN inventory USING (film_id) JOIN rental USING (inventory_id) JOIN payment USING (rental_id) GROUP BY category.name ORDER BY receita_total DESC, categoria"),
        ("film-length-extremes", "agregacao", "Qual a menor e a maior duração de filme por classificação indicativa?", "SELECT rating, MIN(length) AS menor_duracao, MAX(length) AS maior_duracao FROM film GROUP BY rating ORDER BY rating"),
        ("sales-by-store-view", "view", "Qual o total de vendas por loja segundo a view de vendas?", "SELECT store, total_sales FROM sales_by_store ORDER BY store"),
    ]
    return [EvaluationSpec(*row) for row in rows]


def execute_spec(spec: EvaluationSpec, *, container: str, database: str) -> dict[str, Any]:
    policy = ReadOnlySqlPolicy().validate(spec.sql)
    if not policy.allowed or policy.normalized_sql is None:
        raise ValueError(f"Consulta fora da política: {spec.identifier}")
    try:
        parse_one(policy.normalized_sql, read="postgres")
    except ParseError as error:
        raise ValueError(f"Consulta inválida para PostgreSQL: {spec.identifier}") from error
    result = subprocess.run(
        ["docker", "exec", container, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database, "-At", "-c", policy.normalized_sql],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = result.stdout
    return {
        "id": spec.identifier,
        "category": spec.category,
        "question": spec.question,
        "sql": policy.normalized_sql,
        "result_rows": len([line for line in output.splitlines() if line]),
        "result_sha256": sha256(output.encode("utf-8")).hexdigest(),
    }


def generate_evaluation(*, container: str, database: str, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Saída já existe: {output}")
    output.mkdir(parents=True)
    records = [execute_spec(spec, container=container, database=database) for spec in build_specs()]
    with (output / "evaluation.jsonl").open("x", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            file.write("\n")
    report = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "database": database,
        "container": container,
        "examples": len(records),
        "categories": sorted({record["category"] for record in records}),
        "output": str(output),
        "result_values_versioned": False,
    }
    with (output / "report.json").open("x", encoding="utf-8", newline="\n") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    return report


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="sqllm-pagila-postgres")
    parser.add_argument("--database", default="pagila")
    parser.add_argument("--label", default="v18-fc7a867")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    output = ROOT / "data" / "evaluations" / "pagila" / arguments.label
    print(json.dumps(generate_evaluation(container=arguments.container, database=arguments.database, output=output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Especificações públicas PT-BR para o currículo relacional Olist."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class OlistSpec:
    identifier: str
    family: str
    tier: str
    pack: str
    question: str
    sql: str


def _quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _values(connection: sqlite3.Connection, sql: str, limit: int) -> list[str]:
    rows = connection.execute(sql, (limit,)).fetchall()
    return [str(row[0]) for row in rows if row[0] is not None]


def build_specs(connection: sqlite3.Connection) -> list[OlistSpec]:
    states = _values(
        connection,
        "SELECT customer_state FROM customers GROUP BY customer_state ORDER BY COUNT(*) DESC, customer_state LIMIT ?",
        12,
    )
    seller_states = _values(
        connection,
        "SELECT seller_state FROM sellers GROUP BY seller_state ORDER BY COUNT(*) DESC, seller_state LIMIT ?",
        12,
    )
    categories = _values(
        connection,
        "SELECT t.product_category_name_english FROM order_items i "
        "JOIN products p ON p.product_id = i.product_id "
        "JOIN product_category_name_translation t ON t.product_category_name = p.product_category_name "
        "GROUP BY t.product_category_name_english ORDER BY COUNT(*) DESC, t.product_category_name_english LIMIT ?",
        12,
    )
    statuses = _values(
        connection,
        "SELECT order_status FROM orders GROUP BY order_status ORDER BY COUNT(*) DESC, order_status LIMIT ?",
        4,
    )
    payment_types = _values(
        connection,
        "SELECT payment_type FROM order_payments WHERE payment_type <> 'not_defined' "
        "GROUP BY payment_type ORDER BY COUNT(*) DESC, payment_type LIMIT ?",
        3,
    )
    if min(len(states), len(seller_states), len(categories)) < 12 or len(statuses) < 3 or len(payment_types) < 2:
        raise RuntimeError("O espelho Olist não contém valores suficientes para o corpus planejado.")

    specs: list[OlistSpec] = []
    for position, state in enumerate(states, start=1):
        specs.append(
            OlistSpec(
                f"olist-customer-state-orders-{position:02d}",
                "olist-customer-state-orders",
                "small",
                "customers-orders",
                f"Quantos pedidos foram feitos por clientes do estado {state}?",
                "SELECT COUNT(*) AS total_pedidos FROM customers AS c JOIN orders AS o "
                f"ON o.customer_id = c.customer_id WHERE c.customer_state = {_quoted(state)}",
            )
        )
    for month in range(1, 13):
        specs.append(
            OlistSpec(
                f"olist-order-month-count-{month:02d}",
                "olist-order-month-count",
                "small",
                "customers-orders",
                f"Quantos pedidos foram comprados no mês {month} de 2017?",
                "SELECT COUNT(*) AS total_pedidos FROM orders "
                f"WHERE strftime('%Y', order_purchase_timestamp) = '2017' AND CAST(strftime('%m', order_purchase_timestamp) AS INTEGER) = {month}",
            )
        )
    payment_status_pairs = [(payment, status) for payment in payment_types for status in statuses][:12]
    while len(payment_status_pairs) < 12:
        payment_status_pairs.extend(payment_status_pairs[: 12 - len(payment_status_pairs)])
    for position, (payment, status) in enumerate(payment_status_pairs, start=1):
        specs.append(
            OlistSpec(
                f"olist-payment-status-total-{position:02d}",
                "olist-payment-status-total",
                "small",
                "orders-payments",
                f"Qual é o valor total pago por {payment} em pedidos com status {status}?",
                "SELECT ROUND(SUM(p.payment_value), 2) AS valor_total FROM orders AS o "
                "JOIN order_payments AS p ON p.order_id = o.order_id "
                f"WHERE p.payment_type = {_quoted(payment)} AND o.order_status = {_quoted(status)}",
            )
        )
    review_variants = [(score, has_comment) for score in range(1, 6) for has_comment in (False, True)] + [(1, None), (5, None)]
    for position, (score, has_comment) in enumerate(review_variants, start=1):
        if has_comment is True:
            suffix = " e possuem comentário"
            predicate = " AND review_comment_message IS NOT NULL"
        elif has_comment is False:
            suffix = " e não possuem comentário"
            predicate = " AND review_comment_message IS NULL"
        else:
            suffix = ""
            predicate = ""
        specs.append(
            OlistSpec(
                f"olist-review-score-comments-{position:02d}",
                "olist-review-score-comments",
                "small",
                "orders-reviews",
                f"Quantas avaliações têm nota {score}{suffix}?",
                f"SELECT COUNT(*) AS total_avaliacoes FROM order_reviews WHERE review_score = {score}{predicate}",
            )
        )
    for position, state in enumerate(seller_states, start=1):
        specs.append(
            OlistSpec(
                f"olist-seller-state-items-{position:02d}",
                "olist-seller-state-items",
                "small",
                "items-sellers",
                f"Quantos itens foram vendidos por vendedores do estado {state}?",
                "SELECT COUNT(*) AS total_itens FROM order_items AS i JOIN sellers AS s "
                f"ON s.seller_id = i.seller_id WHERE s.seller_state = {_quoted(state)}",
            )
        )
    for position, category in enumerate(categories, start=1):
        specs.append(
            OlistSpec(
                f"olist-category-items-{position:02d}",
                "olist-category-items",
                "small",
                "catalog-sales",
                f"Quantos itens vendidos pertencem à categoria traduzida como {category}?",
                "SELECT COUNT(*) AS total_itens FROM order_items AS i "
                "JOIN products AS p ON p.product_id = i.product_id "
                "JOIN product_category_name_translation AS t ON t.product_category_name = p.product_category_name "
                f"WHERE t.product_category_name_english = {_quoted(category)}",
            )
        )

    for position, (category, status) in enumerate(
        [(category, status) for category in categories[:5] for status in statuses[:2]], start=1
    ):
        specs.append(
            OlistSpec(
                f"olist-category-revenue-status-{position:02d}",
                "olist-category-revenue-status",
                "medium",
                "catalog-sales",
                f"Qual é o valor total de itens e frete da categoria {category} em pedidos {status}?",
                "SELECT ROUND(SUM(i.price + i.freight_value), 2) AS valor_total FROM orders AS o "
                "JOIN order_items AS i ON i.order_id = o.order_id "
                "JOIN products AS p ON p.product_id = i.product_id "
                "JOIN product_category_name_translation AS t ON t.product_category_name = p.product_category_name "
                f"WHERE t.product_category_name_english = {_quoted(category)} AND o.order_status = {_quoted(status)}",
            )
        )
    for position, state in enumerate(states[:10], start=1):
        specs.append(
            OlistSpec(
                f"olist-state-order-finance-{position:02d}",
                "olist-state-order-finance",
                "medium",
                "order-finance",
                f"Para clientes de {state}, qual é o total de itens, frete e pagamentos dos pedidos?",
                "WITH item_totals AS (SELECT order_id, SUM(price) AS itens, SUM(freight_value) AS frete "
                "FROM order_items GROUP BY order_id), payment_totals AS (SELECT order_id, SUM(payment_value) AS pagamentos "
                "FROM order_payments GROUP BY order_id) SELECT ROUND(SUM(it.itens), 2) AS total_itens, "
                "ROUND(SUM(it.frete), 2) AS total_frete, ROUND(SUM(pt.pagamentos), 2) AS total_pagamentos "
                "FROM customers AS c JOIN orders AS o ON o.customer_id = c.customer_id "
                "JOIN item_totals AS it ON it.order_id = o.order_id JOIN payment_totals AS pt ON pt.order_id = o.order_id "
                f"WHERE c.customer_state = {_quoted(state)}",
            )
        )
    for position, (score, payment) in enumerate(
        [(score, payment) for score in range(1, 6) for payment in payment_types[:2]], start=1
    ):
        specs.append(
            OlistSpec(
                f"olist-customer-review-payment-{position:02d}",
                "olist-customer-review-payment",
                "medium",
                "customer-experience",
                f"Quantos clientes distintos avaliaram com nota {score} e pagaram por {payment}?",
                "SELECT COUNT(DISTINCT c.customer_id) AS total_clientes FROM customers AS c "
                "JOIN orders AS o ON o.customer_id = c.customer_id JOIN order_reviews AS r ON r.order_id = o.order_id "
                "JOIN order_payments AS p ON p.order_id = o.order_id "
                f"WHERE r.review_score = {score} AND p.payment_type = {_quoted(payment)}",
            )
        )

    heavy_pairs = [(state, category) for state in states[:3] for category in categories[:3]]
    for position, (state, category) in enumerate(heavy_pairs, start=1):
        specs.append(
            OlistSpec(
                f"olist-heavy-positive-commerce-{position:02d}",
                "olist-heavy-positive-commerce",
                "heavy",
                "commerce-end-to-end",
                f"Quantos pedidos entregues de clientes de {state}, na categoria {category}, tiveram avaliação ao menos 4 e pagamento por cartão de crédito?",
                "SELECT COUNT(DISTINCT o.order_id) AS total_pedidos FROM customers AS c "
                "JOIN orders AS o ON o.customer_id = c.customer_id JOIN order_items AS i ON i.order_id = o.order_id "
                "JOIN products AS pr ON pr.product_id = i.product_id JOIN sellers AS s ON s.seller_id = i.seller_id "
                "JOIN order_payments AS p ON p.order_id = o.order_id JOIN order_reviews AS r ON r.order_id = o.order_id "
                "JOIN product_category_name_translation AS t ON t.product_category_name = pr.product_category_name "
                f"WHERE c.customer_state = {_quoted(state)} AND t.product_category_name_english = {_quoted(category)} "
                "AND o.order_status = 'delivered' AND r.review_score >= 4 AND p.payment_type = 'credit_card'",
            )
        )
    for position, (seller_state, category) in enumerate(
        [(state, category) for state in seller_states[:3] for category in categories[:3]], start=1
    ):
        specs.append(
            OlistSpec(
                f"olist-heavy-negative-commerce-{position:02d}",
                "olist-heavy-negative-commerce",
                "heavy",
                "commerce-end-to-end",
                f"Quantos pedidos da categoria {category}, vendidos por vendedores de {seller_state}, receberam nota até 2 e pagamento por boleto?",
                "SELECT COUNT(DISTINCT o.order_id) AS total_pedidos FROM customers AS c "
                "JOIN orders AS o ON o.customer_id = c.customer_id JOIN order_items AS i ON i.order_id = o.order_id "
                "JOIN products AS pr ON pr.product_id = i.product_id JOIN sellers AS s ON s.seller_id = i.seller_id "
                "JOIN order_payments AS p ON p.order_id = o.order_id JOIN order_reviews AS r ON r.order_id = o.order_id "
                "JOIN product_category_name_translation AS t ON t.product_category_name = pr.product_category_name "
                f"WHERE s.seller_state = {_quoted(seller_state)} AND t.product_category_name_english = {_quoted(category)} "
                "AND r.review_score <= 2 AND p.payment_type = 'boleto'",
            )
        )
    return specs

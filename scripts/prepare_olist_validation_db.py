"""Cria um espelho SQLite indexado do Olist sem modificar o arquivo raw."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "raw" / "kaggle__terencicp__olist-sqlite" / "olist.sqlite"
DEFAULT_OUTPUT = ROOT / "data" / "interim" / "olist-validation.sqlite"

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(customer_state)",
    "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_status_purchase ON orders(order_status, order_purchase_timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_items_seller ON order_items(seller_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_order ON order_payments(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_type ON order_payments(payment_type)",
    "CREATE INDEX IF NOT EXISTS idx_reviews_order ON order_reviews(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_reviews_score ON order_reviews(review_score)",
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products(product_category_name)",
    "CREATE INDEX IF NOT EXISTS idx_sellers_state ON sellers(seller_state)",
    "CREATE INDEX IF NOT EXISTS idx_translation_category ON product_category_name_translation(product_category_name)",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def prepare(source: Path, output: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Espelho Olist não encontrado: {source}")
    if output.exists():
        raise FileExistsError(f"Saída já existe; não será sobrescrita: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    try:
        connection = sqlite3.connect(output)
        try:
            connection.execute("PRAGMA journal_mode = DELETE")
            for statement in INDEXES:
                connection.execute(statement)
            connection.commit()
            check = connection.execute("PRAGMA integrity_check").fetchone()
            if check != ("ok",):
                raise RuntimeError(f"Falha no integrity_check: {check}")
        finally:
            connection.close()
    except Exception:
        output.unlink(missing_ok=True)
        raise


def main() -> None:
    arguments = parse_arguments()
    prepare(arguments.source, arguments.output)
    print(arguments.output)


if __name__ == "__main__":
    main()

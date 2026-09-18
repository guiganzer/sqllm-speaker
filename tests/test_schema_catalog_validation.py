import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from llm_to_sql.agentic.prompt_specializer import PromptTemplate, build_schema_fk_messages
from llm_to_sql.agentic.sqlite_validator import SqliteCatalogValidator
from llm_to_sql.schema_catalog import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


def sample_catalog(database_path: str | None = None) -> SchemaCatalog:
    return SchemaCatalog.from_dict(
        {
            "name": "sample",
            "dialect": "sqlite",
            "database_path": database_path,
            "tables": {
                "customers": {
                    "columns": [{"name": "customer_id", "type": "TEXT"}],
                    "primary_key": ["customer_id"],
                },
                "orders": {
                    "columns": [
                        {"name": "order_id", "type": "TEXT"},
                        {"name": "customer_id", "type": "TEXT"},
                    ],
                    "primary_key": ["order_id"],
                },
                "secret": {
                    "columns": [{"name": "value", "type": "TEXT"}],
                    "primary_key": [],
                },
            },
            "relationships": [
                {
                    "from_table": "orders",
                    "from_columns": ["customer_id"],
                    "to_table": "customers",
                    "to_columns": ["customer_id"],
                    "kind": "hard",
                }
            ],
            "packs": {
                "orders-customers": {
                    "tier": "small",
                    "tables": ["orders", "customers"],
                    "purpose": "Pedidos por cliente.",
                }
            },
        }
    )


class SchemaCatalogTests(unittest.TestCase):
    def test_renders_only_pack_tables_and_relationships(self) -> None:
        context = sample_catalog().render_pack("orders-customers")
        self.assertIn("CREATE TABLE orders", context)
        self.assertIn("orders.customer_id -> customers.customer_id", context)
        self.assertNotIn("CREATE TABLE secret", context)

    def test_builds_fk_oriented_prompt(self) -> None:
        template = PromptTemplate(
            "test-v1",
            "Responda somente SQL.",
            "<dialeto>{dialect}</dialeto>\n<schema>{schema}</schema>\n<pergunta>{question}</pergunta>",
        )
        messages = build_schema_fk_messages(
            question="Quantos pedidos?",
            catalog=sample_catalog(),
            pack_name="orders-customers",
            template=template,
        )
        self.assertIn("Quantos pedidos?", messages[1]["content"])
        self.assertIn("orders.customer_id -> customers.customer_id", messages[1]["content"])

    def test_loads_versioned_public_catalogs(self) -> None:
        olist = SchemaCatalog.load(ROOT / "configs" / "datasets" / "olist.json")
        logistics = SchemaCatalog.load(ROOT / "configs" / "datasets" / "logistics.json")

        self.assertEqual(olist.source["role"], "canonical_public_csv")
        self.assertEqual(len(olist.tables), 9)
        self.assertEqual(olist.pack("commerce-end-to-end").tier, "heavy")
        self.assertEqual(len(logistics.tables), 14)
        self.assertEqual(logistics.pack("loads-customers-routes").tier, "small")

    def test_relation_pack_sizes_match_curriculum_tiers(self) -> None:
        for filename in ("olist.json", "logistics.json"):
            catalog = SchemaCatalog.load(ROOT / "configs" / "datasets" / filename)
            for pack in catalog.packs.values():
                if pack.tier == "small":
                    self.assertLessEqual(len(pack.tables), 3)
                elif pack.tier == "medium":
                    self.assertIn(len(pack.tables), {4, 5})
                else:
                    self.assertGreaterEqual(len(pack.tables), 6)

class SqliteCatalogValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "test.sqlite"
        connection = sqlite3.connect(self.path)
        connection.executescript(
            "CREATE TABLE customers (customer_id TEXT PRIMARY KEY);"
            "CREATE TABLE orders (order_id TEXT PRIMARY KEY, customer_id TEXT);"
            "CREATE TABLE secret (value TEXT);"
            "INSERT INTO customers VALUES ('c1');"
            "INSERT INTO orders VALUES ('o1', 'c1');"
            "INSERT INTO orders VALUES ('o2', 'c1');"
        )
        connection.commit()
        connection.close()
        self.validator = SqliteCatalogValidator(catalog=sample_catalog(), database_path=self.path)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_executes_read_only_query_and_limits_rows(self) -> None:
        result = self.validator.validate_and_execute(
            "SELECT order_id FROM orders ORDER BY order_id",
            pack_name="orders-customers",
            max_rows=1,
        )
        self.assertTrue(result.approved)
        self.assertTrue(result.executed)
        self.assertTrue(result.truncated)
        self.assertEqual(len(result.rows), 1)

    def test_rejects_table_outside_pack(self) -> None:
        result = self.validator.validate_and_execute(
            "SELECT value FROM secret",
            pack_name="orders-customers",
        )
        self.assertFalse(result.approved)
        self.assertIn("fora do pack", result.reason)

    def test_rejects_write_before_database(self) -> None:
        result = self.validator.validate_and_execute(
            "DELETE FROM orders",
            pack_name="orders-customers",
        )
        self.assertFalse(result.approved)


if __name__ == "__main__":
    unittest.main()

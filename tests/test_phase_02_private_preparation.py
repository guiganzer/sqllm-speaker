import unittest

from llm_to_sql.private_data import EndpointSnapshot, build_private_examples, fingerprint, split_private_examples


BASE_SCHEMA = "CREATE TABLE clientes (id INTEGER, nome TEXT)"
ENDPOINT_SCHEMA = "CREATE TABLE raw_pedidos (id INTEGER, cliente_id INTEGER, total NUMERIC)"


class PrivatePreparationTests(unittest.TestCase):
    def test_accepts_readonly_examples_and_creates_three_deterministic_partitions(self) -> None:
        rows = [
            {"id": index, "pergunta": f"Liste cliente {index}", "sql": f"SELECT id, nome FROM clientes WHERE id = {index}", "somente_leitura": True}
            for index in range(1, 51)
        ]
        examples, rejected, dynamic_rows = build_private_examples(
            rows, base_schema=BASE_SCHEMA, endpoint_snapshots=None, dialect="postgres", max_characters=10_000, max_schema_characters=1_000
        )
        train, validation, test = split_private_examples(examples, validation_percent=10, test_percent=10)
        self.assertFalse(rejected)
        self.assertEqual(dynamic_rows, 0)
        self.assertEqual(len(examples), len(train) + len(validation) + len(test))
        self.assertTrue(train and validation and test)
        self.assertEqual(
            {example["source"]["id"] for example in train + validation + test},
            {example["source"]["id"] for example in examples},
        )

    def test_uses_endpoint_snapshot_and_rejects_unknown_or_unsafe_records(self) -> None:
        snapshots = {"pedidos": EndpointSnapshot("pedidos", ENDPOINT_SCHEMA, fingerprint(ENDPOINT_SCHEMA))}
        rows = [
            {"pergunta": "Liste pedidos", "sql": "SELECT id, total FROM raw_pedidos", "endpoint_id": "pedidos", "somente_leitura": True},
            {"pergunta": "Altere cliente", "sql": "UPDATE clientes SET nome = 'x'", "somente_leitura": False},
            {"pergunta": "Endpoint ausente", "sql": "SELECT id FROM raw_pedidos", "endpoint_id": "nao-existe", "somente_leitura": True},
        ]
        examples, rejected, dynamic_rows = build_private_examples(
            rows, base_schema=BASE_SCHEMA, endpoint_snapshots=snapshots, dialect="postgres", max_characters=10_000, max_schema_characters=1_000
        )
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["endpoint_id"], "pedidos")
        self.assertIn(ENDPOINT_SCHEMA, examples[0]["messages"][1]["content"])
        self.assertEqual(dynamic_rows, 1)
        self.assertEqual(rejected["not_marked_readonly"], 1)
        self.assertEqual(rejected["unknown_endpoint"], 1)

    def test_rejects_duplicate_question_sql_for_same_snapshot(self) -> None:
        row = {"pergunta": "Liste clientes", "sql": "SELECT id FROM clientes", "somente_leitura": True}
        examples, rejected, _ = build_private_examples(
            [row, row], base_schema=BASE_SCHEMA, endpoint_snapshots=None, dialect="postgres", max_characters=10_000, max_schema_characters=1_000
        )
        self.assertEqual(len(examples), 1)
        self.assertEqual(rejected["duplicate"], 1)

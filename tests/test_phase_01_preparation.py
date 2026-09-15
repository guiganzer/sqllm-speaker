import unittest

from scripts.prepare_phase_01 import prepare_examples


SOURCE = {"dataset_id": "test/source", "revision": "abc123"}


class PhaseOnePreparationTests(unittest.TestCase):
    def test_normalizes_and_groups_schema_without_leakage(self) -> None:
        rows = [
            {"pergunta": "  Liste\nclientes ", "contexto": "CREATE TABLE clientes (id INT)", "resposta": "SELECT id FROM clientes"},
            {"pergunta": "Conte clientes", "contexto": "CREATE TABLE clientes (id INT)", "resposta": "SELECT COUNT(*) FROM clientes"},
        ]
        train, validation, rejected, groups = prepare_examples(
            rows, validation_percent=10, max_characters=1000, source=SOURCE
        )
        self.assertEqual(len(train) + len(validation), 2)
        self.assertEqual(groups, 1)
        self.assertFalse(rejected)
        self.assertTrue(train or validation)
        self.assertFalse(train and validation)

    def test_rejects_invalid_and_duplicate_sql(self) -> None:
        valid = {"pergunta": "Liste", "contexto": "CREATE TABLE t (id INT)", "resposta": "SELECT id FROM t"}
        invalid = {"pergunta": "Quebre", "contexto": "CREATE TABLE t (id INT)", "resposta": "SELECT FROM"}
        train, validation, rejected, _ = prepare_examples(
            [valid, valid, invalid], validation_percent=10, max_characters=1000, source=SOURCE
        )
        self.assertEqual(len(train) + len(validation), 1)
        self.assertEqual(rejected["duplicate"], 1)
        self.assertEqual(rejected["invalid_sql"], 1)

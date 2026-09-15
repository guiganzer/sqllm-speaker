import unittest

from llm_to_sql.agentic.policy import ReadOnlySqlPolicy


class ReadOnlySqlPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ReadOnlySqlPolicy()

    def test_accepts_single_select(self) -> None:
        result = self.policy.validate("SELECT id, nome FROM clientes;")
        self.assertTrue(result.allowed)
        self.assertEqual(result.normalized_sql, "SELECT id, nome FROM clientes")

    def test_rejects_write_operation(self) -> None:
        self.assertFalse(self.policy.validate("UPDATE clientes SET ativo = 0").allowed)

    def test_rejects_multiple_statements(self) -> None:
        self.assertFalse(self.policy.validate("SELECT 1; SELECT 2").allowed)

    def test_rejects_write_hidden_after_cte(self) -> None:
        sql = "WITH removed AS (DELETE FROM clientes RETURNING id) SELECT * FROM removed"
        self.assertFalse(self.policy.validate(sql).allowed)

    def test_allows_select_with_comment(self) -> None:
        result = self.policy.validate("-- consulta permitida\nSELECT id FROM clientes")
        self.assertTrue(result.allowed)

import unittest

from llm_to_sql.evaluation import aggregate_assessments, assess_sql, deterministic_stratified_sample


DDL = "CREATE TABLE vendas (id INTEGER, cliente TEXT, valor REAL);"


def record(sql: str) -> dict:
    return {
        "schema_group": sql,
        "messages": [
            {"role": "system", "content": "x"},
            {"role": "user", "content": "x"},
            {"role": "assistant", "content": sql},
        ],
    }


class EvaluationTests(unittest.TestCase):
    def test_accepts_sql_with_existing_schema_references(self) -> None:
        result = assess_sql("SELECT cliente, valor FROM vendas", DDL)
        self.assertTrue(result.parses)
        self.assertTrue(result.sql_only)
        self.assertTrue(result.schema_references_valid)

    def test_rejects_prose_and_unknown_column(self) -> None:
        prose = assess_sql("Aqui está: SELECT cliente FROM vendas", DDL)
        unknown_column = assess_sql("SELECT segredo FROM vendas", DDL)
        self.assertFalse(prose.sql_only)
        self.assertFalse(unknown_column.columns_valid)

    def test_sampling_is_deterministic_and_bounded(self) -> None:
        records = [
            record("SELECT cliente FROM vendas"),
            record("SELECT valor FROM vendas ORDER BY valor"),
            record("SELECT cliente, COUNT(*) FROM vendas GROUP BY cliente"),
            record("SELECT id FROM vendas"),
        ]
        first = deterministic_stratified_sample(records, 3)
        self.assertEqual(first, deterministic_stratified_sample(records, 3))
        self.assertEqual(len(first), 3)

    def test_aggregates_rates(self) -> None:
        values = [assess_sql("SELECT id FROM vendas", DDL), assess_sql("DROP TABLE vendas", DDL)]
        metrics = aggregate_assessments(values)
        self.assertEqual(metrics["examples"], 2)
        self.assertEqual(metrics["parses_count"], 1)

import unittest

from llm_to_sql.evaluation import canonical_sql, aggregate_assessments, assess_sql, deterministic_stratified_sample, normalize_model_output


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

    def test_removes_only_qwen_thinking_protocol_markers(self) -> None:
        self.assertEqual(normalize_model_output("</think>\nSELECT id FROM vendas"), "SELECT id FROM vendas")
        self.assertEqual(normalize_model_output("Aqui está: SELECT id FROM vendas"), "Aqui está: SELECT id FROM vendas")

    def test_accepts_double_quoted_text_value_used_by_source_dataset(self) -> None:
        result = assess_sql('SELECT cliente FROM vendas WHERE cliente = "Maria Silva"', DDL)
        self.assertTrue(result.schema_references_valid)

    def test_canonical_sql_ignores_layout_not_query_structure(self) -> None:
        self.assertEqual(canonical_sql("SELECT  id  FROM vendas"), canonical_sql("SELECT id FROM vendas"))

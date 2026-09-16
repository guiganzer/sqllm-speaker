import subprocess
import unittest
from unittest.mock import patch

from llm_to_sql.agentic.pagila_tools import PagilaAgentTools


class PagilaAgentToolsTests(unittest.TestCase):
    def test_rejects_unsafe_sql_without_calling_docker(self) -> None:
        tools = PagilaAgentTools()
        with patch("llm_to_sql.agentic.pagila_tools.subprocess.run") as run:
            result = tools.execute_readonly_sql("DELETE FROM film")
        self.assertFalse(result.approved)
        run.assert_not_called()

    def test_rejects_invalid_table_identifier_without_calling_docker(self) -> None:
        tools = PagilaAgentTools()
        with patch.object(tools, "_run_tsv") as run:
            with self.assertRaises(ValueError):
                tools.get_table_schema("film; DROP TABLE film")
        run.assert_not_called()

    def test_limits_select_with_wrapper_and_returns_rows(self) -> None:
        tools = PagilaAgentTools()
        with patch.object(tools, "_run_tsv", return_value=[("1",), ("2",)]) as run:
            result = tools.execute_readonly_sql("SELECT film_id FROM film", max_rows=2)
        self.assertTrue(result.approved)
        self.assertTrue(result.truncated)
        self.assertEqual(result.rows, (("1",), ("2",)))
        self.assertIn("LIMIT 2", run.call_args.args[0])

    def test_profile_is_structured(self) -> None:
        tools = PagilaAgentTools()
        with patch.object(tools, "_run_tsv", return_value=[("18.6", "23", "9", "1000")]):
            profile = tools.get_database_profile()
        self.assertEqual(profile["dialect"], "postgres")
        self.assertTrue(profile["read_only"])

    def test_execution_error_is_sanitized(self) -> None:
        tools = PagilaAgentTools()
        error = subprocess.CalledProcessError(1, ["docker"], stderr="ERROR: column x does not exist\nsecret")
        with patch.object(tools, "_run_tsv", side_effect=error):
            result = tools.execute_readonly_sql("SELECT x FROM film")
        self.assertTrue(result.approved)
        self.assertEqual(result.error, "ERROR: column x does not exist")

    def test_enriched_schema_has_relationships_cardinality_and_safe_hints(self) -> None:
        tools = PagilaAgentTools()
        responses = [
            [("film_id", "integer", "NO", "")],
            [("PRIMARY KEY", "film_id", "film", "film_id")],
            [("1000",)],
            [("G",), ("PG",)],
            [("Trailers",)],
        ]
        with patch.object(tools, "_run_tsv", side_effect=responses) as run:
            schema = tools.get_enriched_table_schema("film")
            cached = tools.get_enriched_table_schema("film")
        self.assertEqual(schema, cached)
        self.assertIn("-- cardinality: 1000 rows", schema)
        self.assertIn("-- primary key: film.film_id", schema)
        self.assertIn("-- values film.rating: G, PG", schema)
        self.assertEqual(run.call_count, 5)

    def test_enriched_schema_rejects_invalid_identifier(self) -> None:
        tools = PagilaAgentTools()
        with patch.object(tools, "_run_tsv") as run:
            with self.assertRaises(ValueError):
                tools.get_enriched_table_schema("film; DROP TABLE film")
        run.assert_not_called()
import unittest

from llm_to_sql.agentic.context_compiler import ContextCompilationError, compile_schema_context, extract_relation_names


SCHEMAS = {
    "film": "CREATE TABLE public.film (film_id integer NOT NULL, title text);",
    "category": "CREATE TABLE public.category (category_id integer NOT NULL, name text);",
    "film_category": "CREATE TABLE public.film_category (film_id integer, category_id integer);",
}


class ContextCompilerTests(unittest.TestCase):
    def test_extracts_unique_relations_and_ignores_cte_alias(self) -> None:
        sql = "WITH ranked AS (SELECT film_id FROM film) SELECT category.name FROM ranked JOIN film_category USING (film_id) JOIN category USING (category_id)"
        self.assertEqual(extract_relation_names(sql), ("film_category", "category", "film"))

    def test_compiles_only_referenced_schema(self) -> None:
        context = compile_schema_context(
            "SELECT film.title FROM film JOIN film_category USING (film_id)", SCHEMAS.__getitem__, max_characters=1_000
        )
        self.assertEqual(context.relations, ("film", "film_category"))
        self.assertIn("public.film", context.ddl)
        self.assertNotIn("public.category", context.ddl)

    def test_rejects_context_above_budget(self) -> None:
        with self.assertRaises(ContextCompilationError):
            compile_schema_context("SELECT film_id FROM film", lambda _: "x" * 300, max_characters=256)

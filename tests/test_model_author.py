import unittest

from llm_to_sql.agentic.context_compiler import ContextCompilationError, compile_relations_context
from llm_to_sql.agentic.model_author import build_author_messages


class ModelAuthorTests(unittest.TestCase):
    def test_prompt_limits_author_to_schema_and_sql(self) -> None:
        messages = build_author_messages("Quantos filmes existem?", "CREATE TABLE public.film (film_id integer);")
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("somente", messages[0]["content"].lower())
        self.assertIn("<schema>", messages[1]["content"])
        self.assertIn("Quantos filmes", messages[1]["content"])

    def test_repair_prompt_includes_only_sanitized_error(self) -> None:
        message = build_author_messages("Liste filmes", "CREATE TABLE public.film (title text);", "column titulo does not exist")[1]["content"]
        self.assertIn("<erro_sanitizado>", message)
        self.assertIn("column titulo", message)

    def test_compiles_selected_relations_without_reference_sql(self) -> None:
        schemas = {"film": "CREATE TABLE public.film (film_id integer);"}
        context = compile_relations_context(["film", "film"], schemas.__getitem__, max_characters=256)
        self.assertEqual(context.relations, ("film",))
        with self.assertRaises(ContextCompilationError):
            compile_relations_context(["film; DROP TABLE film"], schemas.__getitem__, max_characters=256)
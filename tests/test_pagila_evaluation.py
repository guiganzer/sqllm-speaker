import unittest

from scripts.generate_pagila_evaluation import build_specs
from llm_to_sql.agentic.policy import ReadOnlySqlPolicy


class PagilaEvaluationTests(unittest.TestCase):
    def test_specs_are_unique_and_read_only(self) -> None:
        specs = build_specs()
        self.assertGreaterEqual(len(specs), 20)
        self.assertEqual(len({spec.identifier for spec in specs}), len(specs))
        self.assertEqual(len({spec.question for spec in specs}), len(specs))
        for spec in specs:
            self.assertTrue(ReadOnlySqlPolicy().validate(spec.sql).allowed, spec.identifier)

    def test_specs_cover_descriptions_joins_and_view(self) -> None:
        categories = {spec.category for spec in build_specs()}
        self.assertTrue({"descricoes", "join", "view"}.issubset(categories))

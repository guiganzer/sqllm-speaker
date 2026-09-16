import unittest

from scripts.evaluate_pagila_phase_01_author import aggregate, rows_hash


class PagilaAuthorEvaluationTests(unittest.TestCase):
    def test_rows_hash_is_stable(self) -> None:
        self.assertEqual(rows_hash((("a", "1"),)), rows_hash((("a", "1"),)))
        self.assertNotEqual(rows_hash((("a", "1"),)), rows_hash((("a", "2"),)))

    def test_aggregate_reports_comparable_rates(self) -> None:
        summary = aggregate(
            [
                {"category": "filmes", "parse_and_scope_valid": True, "policy_allowed": True, "executed": True, "result_match": True, "canonical_exact_match": True},
                {"category": "filmes", "parse_and_scope_valid": True, "policy_allowed": True, "executed": True, "result_match": False, "canonical_exact_match": False},
            ]
        )
        self.assertEqual(summary["examples"], 2)
        self.assertEqual(summary["metrics"]["result_match"]["count"], 1)
        self.assertEqual(summary["metrics"]["result_match"]["rate"], 0.5)
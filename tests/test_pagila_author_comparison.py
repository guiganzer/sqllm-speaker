import unittest

from scripts.compare_pagila_author_evaluations import compare_reports


class PagilaAuthorComparisonTests(unittest.TestCase):
    def test_reports_with_same_contract_produce_delta(self) -> None:
        base = {
            "benchmark_fingerprint_sha256": "a", "total_examples": 2, "max_new_tokens": 128, "max_context_characters": 6000,
            "label": "antes", "summary": {"metrics": {name: {"count": 1, "rate": 0.5} for name in ("parse_and_scope_valid", "policy_allowed", "executed", "result_match", "canonical_exact_match")}},
        }
        candidate = {
            **base, "label": "depois", "summary": {"metrics": {name: {"count": 2, "rate": 1.0} for name in base["summary"]["metrics"]}},
        }
        result = compare_reports(base, candidate)
        self.assertEqual(result["metrics"][0]["delta_count"], 1)
        self.assertEqual(result["metrics"][0]["delta_rate"], 0.5)

    def test_rejects_mismatched_contract(self) -> None:
        base = {"benchmark_fingerprint_sha256": "a", "total_examples": 2, "max_new_tokens": 128, "max_context_characters": 6000}
        candidate = {**base, "max_new_tokens": 256}
        with self.assertRaises(ValueError):
            compare_reports(base, candidate)
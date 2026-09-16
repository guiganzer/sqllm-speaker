import unittest

from llm_to_sql.agentic.candidate_ranker import rank_candidates, score_candidate
from llm_to_sql.evaluation_components import aggregate_component_matches, compare_sql_components


class ComponentEvaluationTests(unittest.TestCase):
    def test_detects_component_specific_mismatch(self) -> None:
        reference = "SELECT category.name, COUNT(*) FROM category JOIN film_category USING (category_id) GROUP BY category.name ORDER BY COUNT(*) DESC LIMIT 5"
        candidate = "SELECT category.name, COUNT(*) FROM category JOIN film_category USING (category_id) GROUP BY category.name ORDER BY COUNT(*) DESC LIMIT 10"
        matches = compare_sql_components(reference, candidate)
        self.assertTrue(matches["relations"])
        self.assertTrue(matches["joins"])
        self.assertTrue(matches["group_by"])
        self.assertFalse(matches["limit"])

    def test_invalid_candidate_fails_all_components(self) -> None:
        matches = compare_sql_components("SELECT title FROM film", "não é sql")
        self.assertFalse(any(matches.values()))

    def test_aggregate_rates(self) -> None:
        report = aggregate_component_matches([{"relations": True}, {"relations": False}])
        self.assertEqual(report["relations"], {"count": 1, "rate": 0.5})


class CandidateRankerTests(unittest.TestCase):
    def test_prefers_count_for_quantity_question(self) -> None:
        ranked = rank_candidates(
            "Quantos filmes existem?",
            ["SELECT title FROM film", "SELECT COUNT(*) FROM film"],
        )
        self.assertIn("COUNT", ranked[0].sql)

    def test_more_than_filter_is_not_treated_as_descending_order(self) -> None:
        ranked = score_candidate(
            "Quantos filmes têm mais de 100 minutos?",
            "SELECT COUNT(*) FROM film WHERE length > 100",
        )
        self.assertNotIn("ordem DESC ausente", ranked.reasons)
    def test_prefers_requested_limit_and_descending_order(self) -> None:
        good = "SELECT title FROM film ORDER BY replacement_cost DESC LIMIT 5"
        bad = "SELECT title FROM film ORDER BY replacement_cost LIMIT 10"
        self.assertGreater(
            score_candidate("Quais os 5 filmes com maior custo?", good).score,
            score_candidate("Quais os 5 filmes com maior custo?", bad).score,
        )


if __name__ == "__main__":
    unittest.main()

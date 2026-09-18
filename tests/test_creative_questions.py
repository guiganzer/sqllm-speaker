import json
import unittest

from llm_to_sql.creative_questions import (
    validate_critic_response,
    validate_writer_candidates,
    validate_writer_response,
)


class CreativeQuestionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = {"aggregation": "COUNT", "literal_values": ["South Australia"]}
        self.questions = [
            "Quantos registros correspondem a South Australia?",
            "Qual é a quantidade de registros associados a South Australia?",
            "Você pode informar quantos registros são de South Australia?",
            "Quantos são de South Australia?",
        ]

    def test_accepts_four_distinct_styles(self) -> None:
        response = json.dumps(
            {
                "candidates": [
                    {"id": f"c{index}", "style": style, "question": question}
                    for index, (style, question) in enumerate(
                        zip(("direta", "analitica", "conversacional", "concisa"), self.questions), start=1
                    )
                ]
            },
            ensure_ascii=False,
        )
        candidates = validate_writer_response(response, self.brief)
        self.assertEqual(len(candidates), 4)

    def test_rejects_candidate_that_drops_literal(self) -> None:
        bad = list(self.questions)
        bad[-1] = "Quantos registros existem?"
        response = json.dumps(
            {
                "candidates": [
                    {"id": f"c{index}", "style": style, "question": question}
                    for index, (style, question) in enumerate(
                        zip(("direta", "analitica", "conversacional", "concisa"), bad), start=1
                    )
                ]
            },
            ensure_ascii=False,
        )
        with self.assertRaises(ValueError):
            validate_writer_response(response, self.brief)

        candidates, rejections = validate_writer_candidates(response, self.brief)
        self.assertEqual(len(candidates), 3)
        self.assertEqual(rejections[0].identifier, "c4")
        self.assertIn("literal obrigatório", rejections[0].error)

    def test_critic_can_only_select_roundtrip_approved_candidate(self) -> None:
        response = json.dumps(
            {"selected_id": "c2", "semantic_fidelity": 5, "naturalness": 5, "clarity": 4, "reason": "Clara."}
        )
        result = validate_critic_response(response, {"c1", "c2"})
        self.assertEqual(result["selected_id"], "c2")

        with self.assertRaises(ValueError):
            validate_critic_response(response, {"c1"})


if __name__ == "__main__":
    unittest.main()

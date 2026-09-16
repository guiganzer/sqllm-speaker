import sys
import unittest
from pathlib import Path

from llm_to_sql.phase_02 import build_specs, canonical_sql

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_pagila_evaluation import build_specs as build_frozen_benchmark
from generate_pagila_specialization_corpus import VALIDATION_FAMILIES_BY_EDITION


class PhaseTwoCorpusTests(unittest.TestCase):
    def test_specs_are_unique_and_parse_as_postgres(self) -> None:
        specs = build_specs()
        self.assertGreaterEqual(len(specs), 100)
        self.assertEqual(len({spec.identifier for spec in specs}), len(specs))
        self.assertEqual(len({" ".join(spec.question.lower().split()) for spec in specs}), len(specs))
        self.assertEqual(len({canonical_sql(spec.sql) for spec in specs}), len(specs))

    def test_v2_extends_v1_without_duplicates(self) -> None:
        v1 = build_specs("v1")
        v2 = build_specs("v2")
        self.assertGreater(len(v2), len(v1))
        self.assertEqual({spec.identifier for spec in v1}, {spec.identifier for spec in v2[: len(v1)]})
        self.assertEqual(len({canonical_sql(spec.sql) for spec in v2}), len(v2))

    def test_frozen_pagila_benchmark_has_no_exact_overlap(self) -> None:
        benchmark = build_frozen_benchmark()
        benchmark_questions = {" ".join(spec.question.lower().split()) for spec in benchmark}
        benchmark_sql = {canonical_sql(spec.sql) for spec in benchmark}
        for spec in build_specs("v2"):
            self.assertNotIn(" ".join(spec.question.lower().split()), benchmark_questions)
            self.assertNotIn(canonical_sql(spec.sql), benchmark_sql)

    def test_split_is_by_family_and_nonempty(self) -> None:
        families = {spec.family for spec in build_specs("v2")}
        v2_validation = VALIDATION_FAMILIES_BY_EDITION["v2"]
        self.assertTrue(v2_validation)
        self.assertTrue(v2_validation <= families)
        self.assertTrue(families - v2_validation)

    def test_v3_is_large_keeps_replay_and_has_family_holdout(self) -> None:
        v2 = build_specs("v2")
        v3 = build_specs("v3")
        self.assertGreaterEqual(len(v3), 2000)
        self.assertEqual(
            {spec.identifier for spec in v2},
            {spec.identifier for spec in v3[: len(v2)]},
        )
        self.assertEqual(len({spec.identifier for spec in v3}), len(v3))
        self.assertEqual(len({" ".join(spec.question.lower().split()) for spec in v3}), len(v3))
        validation = VALIDATION_FAMILIES_BY_EDITION["v3"]
        self.assertTrue(validation <= {spec.family for spec in v3})
        self.assertTrue(all(family.startswith("v3-") for family in validation))
    def test_uses_pagila_smallint_active_flag(self) -> None:
        active_specs = [spec for spec in build_specs() if spec.family == "customer-store-active"]
        self.assertEqual(len(active_specs), 2)
        self.assertTrue(all("active = 1" in spec.sql for spec in active_specs))


if __name__ == "__main__":
    unittest.main()

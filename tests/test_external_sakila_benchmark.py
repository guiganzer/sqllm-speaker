import json
from pathlib import Path
import tempfile
import unittest

from scripts.inspect_external_sakila_benchmark import load_sakila_records, summarize


class ExternalSakilaBenchmarkTests(unittest.TestCase):
    def test_rejects_wrong_sakila_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gold.json"
            path.write_text(json.dumps([]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_sakila_records(path)

    def test_summary_marks_suite_as_validation_only(self) -> None:
        rows = []
        for category_index, category in enumerate(("Aggregation", "Comparison", "Join", "Lookup", "Nested", "Sorting"), start=1):
            for item_index in range(1, 6):
                rows.append({"id": f"SAK-{chr(64 + category_index)}{category_index}-{item_index:02}", "db": "sakila", "category": category, "question_id": "id", "question_en": "en", "solution_sql": "SELECT 1", "expected_rows": []})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gold.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            records = load_sakila_records(path)
            report = summarize(path, records)
        self.assertEqual(report["subset"]["items"], 30)
        self.assertFalse(report["governance"]["allowed_for_training"])
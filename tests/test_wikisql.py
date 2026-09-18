import unittest

from llm_to_sql.wikisql import (
    RestrictedReprError,
    execute_reference,
    parse_query,
    parse_restricted_numpy_repr,
    parse_table,
    render_schema,
    render_sql,
)


TABLE_REPR = """{
'header': array(['State', 'Current slogan', 'Notes'], dtype=object),
'types': array(['text', 'text', 'text'], dtype=object),
'rows': array([
  array(['South Australia', 'SOUTH AUSTRALIA', 'No slogan'], dtype=object),
  array(['Queensland', 'SUNSHINE STATE', 'Active slogan'], dtype=object)
], dtype=object),
'id': '1-1',
'name': 'table_1_1'
}"""

SQL_REPR = """{
'human_readable': 'SELECT Notes FROM table WHERE Current slogan = SOUTH AUSTRALIA',
'sel': 2,
'agg': 0,
'conds': {
  'column_index': array([1], dtype=int32),
  'operator_index': array([0], dtype=int32),
  'condition': array(['SOUTH AUSTRALIA'], dtype=object)
}
}"""


class RestrictedWikiSqlParserTests(unittest.TestCase):
    def test_parses_numpy_repr_without_numpy(self) -> None:
        payload = parse_restricted_numpy_repr("{'values': array([1, -2], dtype=int32)}")
        self.assertEqual(payload, {"values": [1, -2]})

    def test_rejects_arbitrary_function_call(self) -> None:
        with self.assertRaises(RestrictedReprError):
            parse_restricted_numpy_repr("__import__('os').system('whoami')")

    def test_rejects_comprehension(self) -> None:
        with self.assertRaises(RestrictedReprError):
            parse_restricted_numpy_repr("[value for value in range(10)]")


class WikiSqlRenderingTests(unittest.TestCase):
    def test_renders_and_executes_reference(self) -> None:
        table = parse_table(TABLE_REPR)
        query = parse_query(SQL_REPR, column_count=len(table.headers))
        schema = render_schema(table)
        sql = render_sql(table, query)

        self.assertIn('"Current slogan" TEXT', schema)
        self.assertEqual(
            sql,
            'SELECT "Notes" FROM "table_1_1" WHERE "Current slogan" = \'SOUTH AUSTRALIA\'',
        )
        self.assertEqual(execute_reference(table, sql), (("No slogan",),))

    def test_disambiguates_duplicate_headers_by_position(self) -> None:
        table = parse_table(
            "{'header': array(['Name', 'Name'], dtype=object), "
            "'types': array(['text', 'text'], dtype=object), "
            "'rows': array([array(['a', 'b'], dtype=object)], dtype=object), "
            "'name': 'duplicate'}"
        )
        self.assertEqual(table.headers, ("Name", "Name__2"))

    def test_rejects_unknown_operator(self) -> None:
        table = parse_table(TABLE_REPR)
        malicious = SQL_REPR.replace("array([0], dtype=int32)", "array([3], dtype=int32)", 1)
        with self.assertRaises(RestrictedReprError):
            parse_query(malicious, column_count=len(table.headers))


if __name__ == "__main__":
    unittest.main()

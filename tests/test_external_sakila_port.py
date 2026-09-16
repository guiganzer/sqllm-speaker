import unittest

from scripts.port_external_sakila_to_pagila import apply_pagila_compatibility, transpile_mysql_to_postgres
from sqlglot import parse_one


class ExternalSakilaPortTests(unittest.TestCase):
    def test_transpiles_mysql_date_function_to_postgres(self) -> None:
        translated = transpile_mysql_to_postgres("SELECT MONTH(payment_date) FROM payment WHERE YEAR(payment_date) = 2006")
        self.assertIn("EXTRACT", translated)
        self.assertIsNotNone(parse_one(translated, read="postgres"))

    def test_maps_only_documented_pagila_equivalences(self) -> None:
        self.assertIn("LOWER(r.rental_period)", apply_pagila_compatibility("SAK-J2-01", "SELECT r.rental_date FROM rental r"))
        self.assertIn("LOWER(r.rental_period)", apply_pagila_compatibility("SAK-J2-01", 'SELECT r."rental_date" FROM rental r'))
        self.assertIn("WHERE length", apply_pagila_compatibility("SAK-S6-02", "SELECT title FROM film HAVING length = 1"))
    def test_rejects_multiple_statements(self) -> None:
        with self.assertRaises(ValueError):
            transpile_mysql_to_postgres("SELECT 1; SELECT 2")
from django.test import SimpleTestCase

from .management.commands.import_rdc_locations import (
    EXPECTED,
    _is_header_or_total,
    _valid_entity,
    normalize_table_row,
    province_name,
)


class RDCLocationImporterTests(SimpleTestCase):
    def test_reference_counts_are_explicit(self):
        self.assertEqual(EXPECTED["PROVINCE"], 26)
        self.assertEqual(EXPECTED["TERRITORY"], 145)
        self.assertEqual(EXPECTED["CITY"], 99)
        self.assertEqual(EXPECTED["COMMUNE"], 620)
        self.assertEqual(EXPECTED["SECTOR"], 472)
        self.assertEqual(EXPECTED["CHIEFDOM"], 262)

    def test_province_aliases_are_normalized(self):
        self.assertEqual(province_name("HAUT-KATANGA"), "Haut-Katanga")
        self.assertEqual(province_name("KASAI CENTRAL"), "Kasaï-Central")
        self.assertEqual(province_name("TANGANNYIIKA"), "Tanganyika")

    def test_table_cells_are_split_without_empty_values(self):
        row = ["KAMBOVE", "KAMBOVE", "Commune A\nCommune B", "LUFIRA", "BASANGA", ""]
        normalized = normalize_table_row(row)
        self.assertEqual(normalized[0], ["KAMBOVE"])
        self.assertEqual(normalized[1], ["KAMBOVE"])
        self.assertEqual(normalized[2], ["Commune A", "Commune B"])
        self.assertEqual(normalized[3], ["LUFIRA"])
        self.assertEqual(normalized[4], ["BASANGA"])

    def test_headers_and_totals_are_rejected(self):
        self.assertTrue(_is_header_or_total([
            ["TERRITOIRE", "VILLE", "COMMUNE", "SECTEUR", "CHEFFERIE", "OBSERVATION"]
        ]))
        self.assertTrue(_is_header_or_total([
            ["TOTAL ETD"], [], [], [], [], []
        ]))
        self.assertTrue(_valid_entity("KAMINA"))
        self.assertFalse(_valid_entity("TOTAL"))
        self.assertFalse(_valid_entity("123"))

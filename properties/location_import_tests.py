from django.test import SimpleTestCase

from .management.commands.import_rdc_locations import (
    EXPECTED,
    _header_or_total,
    clean,
    norm,
    province_name,
    split_cell,
    valid_entity,
)


class RDCLocationImporterTests(SimpleTestCase):
    def test_official_reference_totals(self):
        self.assertEqual(EXPECTED, {
            "PROVINCE": 26,
            "TERRITORY": 145,
            "CITY": 99,
            "COMMUNE": 620,
            "SECTOR": 472,
            "CHIEFDOM": 262,
        })

    def test_province_aliases_are_normalized(self):
        self.assertEqual(province_name("HAUT-KATANGA"), "Haut-Katanga")
        self.assertEqual(province_name("KASAI CENTRAL"), "Kasaï-Central")
        self.assertEqual(province_name("TANGANNYIIKA"), "Tanganyika")

    def test_cells_are_split_and_cleaned(self):
        self.assertEqual(split_cell("KAMINA\nKAMINA\n SOBONGO "), ["KAMINA", "KAMINA", "SOBONGO"])
        self.assertEqual(clean("  KASAI\u00ad  "), "KASAI")
        self.assertEqual(norm("Kasaï-Central"), "KASAI CENTRAL")

    def test_headers_and_totals_are_rejected(self):
        self.assertTrue(_header_or_total([
            "TERRITOIRE", "VILLE", "COMMUNE", "SECTEUR", "CHEFFERIE", "OBSERVATION"
        ]))
        self.assertTrue(_header_or_total(["TOTAL ETD", "", "", "", "", ""]))
        self.assertTrue(valid_entity("KAMINA"))
        self.assertFalse(valid_entity("TOTAL"))
        self.assertFalse(valid_entity("123"))

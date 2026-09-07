import re
import unittest
from pathlib import Path

from models.text_validation import is_valid_catalog_name
from models.tracking_models.activity import Activity


class ActivitySeedTests(unittest.TestCase):
    def setUp(self):
        self.official_seed = Path("database/seeds/seed_activities_compendium_official.sql").read_text(encoding="utf-8")
        self.mapping_seed = Path("database/seeds/seed_activities_macrosense_mappings.sql").read_text(encoding="utf-8")

    def count_seed_rows(self, sql_text: str) -> int:
        return len(re.findall(r"^\('[^']+", sql_text, flags=re.MULTILINE))

    def get_seed_names(self, sql_text: str) -> list[str]:
        return [
            name.replace("''", "'")
            for name in re.findall(r"^\('((?:''|[^'])*)',", sql_text, flags=re.MULTILINE)
        ]

    def test_official_compendium_seed_has_useful_coverage(self):
        self.assertGreaterEqual(self.count_seed_rows(self.official_seed), 50)
        self.assertIn("'Compendium'", self.official_seed)
        self.assertIn("'official_compendium'", self.official_seed)
        self.assertIn("2024 Adult Compendium of Physical Activities", self.official_seed)
        self.assertIn("Jogging (general)", self.official_seed)
        self.assertIn("General weight training", self.official_seed)

    def test_mapping_seed_marks_practical_gym_exercises_as_macrosense_mappings(self):
        self.assertGreaterEqual(self.count_seed_rows(self.mapping_seed), 30)
        self.assertIn("'MacroSense'", self.mapping_seed)
        self.assertIn("'Compendium-based mapping'", self.mapping_seed)
        self.assertIn("'compendium_mapping'", self.mapping_seed)
        self.assertIn("Machine chest press", self.mapping_seed)
        self.assertIn("Dumbbell biceps curls", self.mapping_seed)
        self.assertIn("Cable triceps extensions", self.mapping_seed)

    def test_mapping_seed_does_not_pretend_practical_ids_are_official_compendium(self):
        self.assertNotIn("MS-MAP-STR-001', 'https://pacompendium.com/conditioning-exercise/', 'MS-MAP", self.mapping_seed)
        self.assertIn("Mapped from", self.mapping_seed)

    def test_seed_names_are_ascii_and_fit_catalog_constraints(self):
        names = self.get_seed_names(self.official_seed) + self.get_seed_names(self.mapping_seed)
        self.assertTrue(names)
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(name.isascii())
                self.assertTrue(is_valid_catalog_name(name))
                self.assertLessEqual(len(name), 100)

    def test_seed_names_have_no_normalized_duplicates_across_catalogs(self):
        names = self.get_seed_names(self.official_seed) + self.get_seed_names(self.mapping_seed)
        normalized_names = [Activity.normalize_name(name) for name in names]
        self.assertEqual(len(normalized_names), len(set(normalized_names)))


if __name__ == "__main__":
    unittest.main()

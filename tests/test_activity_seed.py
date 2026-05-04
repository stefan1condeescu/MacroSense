import re
import unittest
from pathlib import Path


class ActivitySeedTests(unittest.TestCase):
    def setUp(self):
        self.official_seed = Path("database/seeds/seed_activities_compendium_official.sql").read_text(encoding="utf-8")
        self.mapping_seed = Path("database/seeds/seed_activities_macrosense_mappings.sql").read_text(encoding="utf-8")

    def count_seed_rows(self, sql_text: str) -> int:
        return len(re.findall(r"^\('[^']+", sql_text, flags=re.MULTILINE))

    def test_official_compendium_seed_has_useful_coverage(self):
        self.assertGreaterEqual(self.count_seed_rows(self.official_seed), 50)
        self.assertIn("'Compendium'", self.official_seed)
        self.assertIn("'official_compendium'", self.official_seed)
        self.assertIn("2024 Adult Compendium of Physical Activities", self.official_seed)
        self.assertIn("Alergare ușoară generală", self.official_seed)
        self.assertIn("Antrenament cu greutăți general", self.official_seed)

    def test_mapping_seed_marks_practical_gym_exercises_as_macrosense_mappings(self):
        self.assertGreaterEqual(self.count_seed_rows(self.mapping_seed), 30)
        self.assertIn("'MacroSense'", self.mapping_seed)
        self.assertIn("'Compendium-based mapping'", self.mapping_seed)
        self.assertIn("'compendium_mapping'", self.mapping_seed)
        self.assertIn("Chest press la aparat", self.mapping_seed)
        self.assertIn("Biceps curls cu gantere", self.mapping_seed)
        self.assertIn("Triceps extensions la cablu", self.mapping_seed)

    def test_mapping_seed_does_not_pretend_practical_ids_are_official_compendium(self):
        self.assertNotIn("MS-MAP-STR-001', 'https://pacompendium.com/conditioning-exercise/', 'MS-MAP", self.mapping_seed)
        self.assertIn("Mapped from", self.mapping_seed)


if __name__ == "__main__":
    unittest.main()

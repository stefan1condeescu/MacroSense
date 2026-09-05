import ast
import unittest
from pathlib import Path

from ui.translations_ro import ROMANIAN_TRANSLATIONS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS_PATH = PROJECT_ROOT / "ui" / "translations_ro.py"


def collect_literal_translation_keys() -> set[str]:
    """Collect literal English source strings passed to translate()."""
    source_paths = [PROJECT_ROOT / "app.py", *(PROJECT_ROOT / "ui").rglob("*.py")]
    keys = set()
    for source_path in source_paths:
        source_tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(source_tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            is_translate_call = (
                isinstance(node.func, ast.Name) and node.func.id == "translate"
            ) or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "translate"
            )
            source_argument = node.args[0]
            if (
                is_translate_call
                and isinstance(source_argument, ast.Constant)
                and isinstance(source_argument.value, str)
            ):
                keys.add(source_argument.value)
    return keys


def collect_translation_dictionary_keys() -> list[str]:
    """Read dictionary keys from the AST so duplicate literals stay visible."""
    source_tree = ast.parse(TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(source_tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "ROMANIAN_TRANSLATIONS"
            for target in node.targets
        ):
            return [
                key.value
                for key in node.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            ]
    raise AssertionError("ROMANIAN_TRANSLATIONS dictionary was not found.")


class TranslationCatalogTests(unittest.TestCase):
    def test_every_literal_ui_source_text_has_a_romanian_translation(self):
        missing_keys = collect_literal_translation_keys() - ROMANIAN_TRANSLATIONS.keys()

        self.assertEqual(missing_keys, set())

    def test_romanian_translation_dictionary_has_no_duplicate_keys(self):
        literal_keys = collect_translation_dictionary_keys()

        self.assertEqual(len(literal_keys), len(set(literal_keys)))


if __name__ == "__main__":
    unittest.main()

import base64
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from ui import branding


class ImageCollector(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.images = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


class BrandingTests(unittest.TestCase):
    def setUp(self):
        branding._asset_data_uri.cache_clear()
        self.addCleanup(branding._asset_data_uri.cache_clear)

    def test_wordmark_embeds_local_svg_with_accessible_brand_text(self):
        html = branding.brand_wordmark_html()
        images = ImageCollector(html).images

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["alt"], "")
        self.assertIn("<span>MacroSense</span>", html)
        prefix, encoded = images[0]["src"].split(",", 1)
        self.assertEqual(prefix, "data:image/svg+xml;base64")
        self.assertEqual(
            base64.b64decode(encoded, validate=True),
            (branding.BRANDING_DIRECTORY / "macrosense-mark.svg").read_bytes(),
        )

    def test_svg_is_standalone_geometry_without_scripts_or_external_resources(self):
        svg_path = branding.BRANDING_DIRECTORY / "macrosense-mark.svg"
        root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))

        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertIn("viewBox", root.attrib)
        allowed_tags = {"svg", "title", "desc", "g", "rect", "path", "circle", "line"}
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            self.assertIn(tag, allowed_tags)
            for name, value in element.attrib.items():
                attribute = name.rsplit("}", 1)[-1].lower()
                self.assertFalse(attribute.startswith("on"), "No SVG event handlers")
                self.assertNotIn(attribute, {"href", "src", "style"})
                self.assertNotIn("url(", value.lower())

    def test_welcome_photo_is_local_optional_decoration(self):
        images = ImageCollector(branding.welcome_background_html()).images

        self.assertEqual(len(images), 1)
        image = images[0]
        self.assertEqual(image["class"], "auth-welcome-art")
        self.assertEqual(image["alt"], "")
        self.assertEqual(image["aria-hidden"], "true")
        self.assertEqual(image["draggable"], "false")
        prefix, encoded = image["src"].split(",", 1)
        self.assertEqual(prefix, "data:image/png;base64")
        data = base64.b64decode(encoded, validate=True)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(data, (branding.BRANDING_DIRECTORY / "welcome-fruit.png").read_bytes())
        self.assertLessEqual(len(data), 2 * 1024 * 1024, "Keep the login photo below 2 MiB")

    def test_missing_optional_photo_does_not_break_login_decoration(self):
        with patch.object(Path, "read_bytes", side_effect=FileNotFoundError):
            self.assertEqual(branding.welcome_background_html(), "")
        self.assertEqual(branding._asset_data_uri.cache_info().currsize, 0)
        self.assertIn("auth-welcome-art", branding.welcome_background_html())

    def test_bundled_asset_is_read_only_once_between_reruns(self):
        with patch.object(Path, "read_bytes", return_value=b"bundled image") as read_bytes:
            first = branding._asset_data_uri("welcome-fruit.png", "image/png")
            second = branding._asset_data_uri("welcome-fruit.png", "image/png")

        self.assertEqual(first, second)
        read_bytes.assert_called_once_with()

    def test_decoration_does_not_intercept_inputs_and_has_mobile_styling(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")
        art_rule = re.search(r"\.auth-welcome-art\s*\{([^}]+)\}", css_text)

        self.assertIsNotNone(art_rule)
        self.assertRegex(art_rule.group(1), r"pointer-events\s*:\s*none")
        self.assertRegex(art_rule.group(1), r"user-select\s*:\s*none")
        self.assertIn('.stApp:has(.auth-login-panel) [data-testid="stMain"]', css_text)
        self.assertRegex(css_text, r"@media\s*\(max-width:\s*\d+px\)")


if __name__ == "__main__":
    unittest.main()

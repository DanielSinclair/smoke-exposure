from pathlib import Path
import unittest

from PIL import Image

from pipeline.settings import ROOT


class SocialGraphicTests(unittest.TestCase):
    def test_social_graphics_are_complete_and_publishable(self):
        output = ROOT / "site" / "public" / "social"
        expected = {
            "01-modeled-smoke-trend.png",
            "02-monthly-smoke-history.png",
            "03-worst-smoke-days.png",
            "04-burned-area-trendlines.png",
            "05-recent-smoke-comparison.png",
            "06-seasonality-shift.png",
            "07-regional-concentration.png",
            "08-historical-review-coverage.png",
            "09-fire-record-coverage.png",
            "10-2026-fire-activity.png",
        }
        self.assertEqual({path.name for path in output.glob("*.png")}, expected)
        for path in output.glob("*.png"):
            with Image.open(path) as image:
                self.assertEqual(image.size, (2400, 1350))
                self.assertEqual(image.mode, "RGB")
                self.assertTrue(image.info.get("Title"))
                self.assertTrue(image.info.get("Description"))
                self.assertEqual(
                    image.info.get("Source"),
                    "https://github.com/DanielSinclair/smoke-exposure",
                )
                self.assertGreater(len(set(image.resize((64, 36)).get_flattened_data())), 8)

    def test_monthly_graphic_uses_only_data_available_years(self):
        source = (ROOT / "pipeline" / "render_social_graphics.py").read_text()
        self.assertIn('"modeled_comparable", "operational_proxy"', source)
        self.assertNotIn("documented_event\") for month in row", source)

    def test_graphic_set_includes_fact_driven_extensions(self):
        source = (ROOT / "pipeline" / "render_social_graphics.py").read_text()
        for fact in (
            "Modeled seasonal concentration",
            "Five states carried half of the national burden",
            "Most pre-2006 months remain unreviewed",
            "National fire catalogs do not cover every era equally",
            "More than 11 million acres had burned by July 18",
        ):
            self.assertIn(fact, source)


if __name__ == "__main__":
    unittest.main()

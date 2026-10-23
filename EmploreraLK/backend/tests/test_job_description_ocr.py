import io
import unittest
from unittest.mock import Mock
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from PIL import ImageOps

from app.components.forecasting.agents import job_description_ocr
from app.components.forecasting.agents.job_description_ocr import (
    extract_topjobs_image_text,
)


class JobDescriptionOCRTests(unittest.TestCase):
    @staticmethod
    def png_bytes():
        image = Image.new("RGB", (20, 20), "white")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def response(content):
        class FakeResponse:
            def __init__(self, body):
                self.content = body

            @staticmethod
            def raise_for_status():
                return None

        return FakeResponse(content)

    @patch("app.components.forecasting.agents.job_description_ocr.requests.get")
    def test_extracts_and_cleans_text_from_topjobs_image(self, get):
        get.return_value = self.response(self.png_bytes())
        image_to_string = Mock()
        image_to_string.return_value = (
            "  Software   Engineer  \n\n Python and SQL cloud services engineering team "
        )
        with patch.object(
            job_description_ocr,
            "_load_ocr_dependencies",
            return_value=(SimpleNamespace(image_to_string=image_to_string), Image, ImageOps),
        ):
            result = extract_topjobs_image_text(
                ["https://www.topjobs.lk/logo/DEFZZZ/ad.png"]
            )

        self.assertEqual(
            result,
            "Software Engineer\nPython and SQL cloud services engineering team",
        )
        image_to_string.assert_called_once()
        get.assert_called_once()

    @patch("app.components.forecasting.agents.job_description_ocr.requests.get")
    def test_rejects_non_topjobs_image_url(self, get):
        result = extract_topjobs_image_text(["https://example.com/ad.png"])

        self.assertIsNone(result)
        get.assert_not_called()

    @patch("app.components.forecasting.agents.job_description_ocr.requests.get")
    def test_skips_images_over_size_limit(self, get):
        from app.components.forecasting.agents.job_description_ocr import (
            MAX_IMAGE_BYTES,
        )

        get.return_value = self.response(b"x" * (MAX_IMAGE_BYTES + 1))
        image_to_string = Mock()
        with patch.object(
            job_description_ocr,
            "_load_ocr_dependencies",
            return_value=(SimpleNamespace(image_to_string=image_to_string), Image, ImageOps),
        ):
            result = extract_topjobs_image_text(
                ["https://www.topjobs.lk/logo/DEFZZZ/ad.png"]
            )

        self.assertIsNone(result)
        image_to_string.assert_not_called()

    @patch("app.components.forecasting.agents.job_description_ocr.requests.get")
    def test_missing_python_dependency_skips_optional_ocr(self, get):
        original_import = __import__

        def without_pytesseract(name, *args, **kwargs):
            if name == "pytesseract":
                raise ModuleNotFoundError("No module named 'pytesseract'")
            return original_import(name, *args, **kwargs)

        get.return_value = self.response(self.png_bytes())
        with patch("builtins.__import__", side_effect=without_pytesseract):
            result = extract_topjobs_image_text(
                ["https://www.topjobs.lk/logo/DEFZZZ/ad.png"]
            )

        self.assertIsNone(result)
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()

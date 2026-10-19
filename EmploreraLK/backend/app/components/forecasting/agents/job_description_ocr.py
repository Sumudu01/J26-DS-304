import io
import logging
import os
import re
from typing import Iterable, Optional, Tuple
from urllib.parse import urlparse

import requests

logger = logging.getLogger("emploreralk.agents.job_description_ocr")

TOPJOBS_HOST = "topjobs.lk"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000


def _load_ocr_dependencies() -> Optional[Tuple[object, object, object]]:
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as error:
        logger.warning("Optional OCR dependencies are missing; skipping image OCR: %s", error)
        return None

    if os.environ.get("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]

    return pytesseract, Image, ImageOps


def extract_topjobs_image_text(image_urls: Iterable[str]) -> Optional[str]:
    """Download and OCR TopJobs advert images, returning readable English text."""
    valid_image_urls = []
    for image_url in list(image_urls)[:8]:
        parsed_url = urlparse(image_url)
        host = parsed_url.hostname or ""
        if (
            parsed_url.scheme != "https"
            or not (host == TOPJOBS_HOST or host.endswith(f".{TOPJOBS_HOST}"))
            or not parsed_url.path.lower().endswith((".jpg", ".jpeg", ".png"))
        ):
            logger.warning("Skipping invalid TopJobs advert image URL: %s", image_url)
            continue
        valid_image_urls.append(image_url)

    if not valid_image_urls:
        return None

    dependencies = _load_ocr_dependencies()
    if dependencies is None:
        return None
    pytesseract, Image, ImageOps = dependencies
    extracted_text = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EmploreraLKJobDescriptionOCR/1.0)",
        "Referer": "https://www.topjobs.lk/",
    }

    for image_url in valid_image_urls:
        try:
            response = requests.get(image_url, headers=headers, timeout=(5, 25))
            response.raise_for_status()
            if len(response.content) > MAX_IMAGE_BYTES:
                logger.warning("TopJobs advert image exceeds OCR size limit: %s", image_url)
                continue

            with Image.open(io.BytesIO(response.content)) as source_image:
                if source_image.width * source_image.height > MAX_IMAGE_PIXELS:
                    logger.warning("TopJobs advert image exceeds OCR pixel limit: %s", image_url)
                    continue
                image = ImageOps.exif_transpose(source_image).convert("L")
                image = ImageOps.autocontrast(image)
                scale = min(3.0, 1800 / image.width, 4000 / max(image.size))
                if scale > 1:
                    image = image.resize(
                        (round(image.width * scale), round(image.height * scale)),
                        Image.Resampling.LANCZOS,
                    )

            text = pytesseract.image_to_string(
                image,
                lang="eng",
                config="--oem 3 --psm 11",
                timeout=45,
            )
            cleaned_lines = [
                re.sub(r"\s+", " ", line).strip()
                for line in text.splitlines()
                if line.strip()
            ]
            recognized_text = "\n".join(cleaned_lines)
            if sum(character.isalnum() for character in recognized_text) >= 40:
                extracted_text.append(recognized_text)
            else:
                logger.warning("OCR found no readable advert text in %s", image_url)
        except pytesseract.pytesseract.TesseractNotFoundError:
            logger.error(
                "Tesseract OCR executable is not installed or configured; "
                "set TESSERACT_CMD or install Tesseract OCR."
            )
            return None
        except (requests.RequestException, OSError, ValueError, RuntimeError) as error:
            logger.warning("Could not OCR TopJobs advert image %s: %s", image_url, error)
        except Exception:
            logger.exception("Unexpected error OCRing TopJobs advert image %s", image_url)

    return "\n\n".join(extracted_text) or None

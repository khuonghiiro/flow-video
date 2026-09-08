"""Image Validator for Skill Tree Pipeline.

Downloads generated images and performs:
1. Basic pixel checks: size, dimensions, green chroma background ratio
2. Saves to local disk for AI agent (Antigravity) to visually inspect via view_file

The AI agent will call validate_image() → get back local file path + basic results,
then use view_file to look at the image and decide pass/fail.
"""
import asyncio
import io
import logging
from pathlib import Path
from typing import Optional

import aiohttp
import certifi
import ssl

from agent.config import OUTPUT_DIR

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────
MIN_GREEN_RATIO = 0.05  # at least 5% green background expected
MIN_IMAGE_BYTES = 5_000  # reject images smaller than 5KB
VALIDATION_DIR = OUTPUT_DIR / "_validation"


async def download_image(url: str, timeout: int = 30) -> Optional[bytes]:
    """Download image bytes from a CDN URL."""
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, ssl=ssl_ctx,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status != 200:
                    logger.warning("Download failed: HTTP %d for %s", resp.status, url[:80])
                    return None
                data = await resp.read()
                if len(data) < MIN_IMAGE_BYTES:
                    logger.warning("Image too small: %d bytes", len(data))
                    return None
                return data
    except Exception as e:
        logger.warning("Download error: %s", e)
        return None


def save_image(image_bytes: bytes, angle: str, attempt: int = 1) -> Path:
    """Save image to local validation directory for AI agent inspection.

    Returns the absolute path to the saved file.
    """
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"angle_{angle}_attempt_{attempt}.png"
    filepath = VALIDATION_DIR / filename
    filepath.write_bytes(image_bytes)
    logger.info("Saved validation image: %s (%d bytes)", filepath, len(image_bytes))
    return filepath


def basic_checks(image_bytes: bytes) -> dict:
    """Run basic pixel-level checks on image bytes.

    Returns dict with:
      - valid: bool
      - width, height: int
      - green_ratio: float (0-1)
      - issues: list[str]
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed, skipping pixel checks")
        return {"valid": True, "issues": ["pillow_not_installed"]}

    issues = []
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size

    # Check dimensions
    if w < 100 or h < 100:
        issues.append(f"too_small_{w}x{h}")

    # Check aspect ratio (should be roughly 9:16 portrait)
    ratio = w / h
    if ratio > 0.8:
        issues.append(f"wrong_aspect_{ratio:.2f}")

    # Check green chroma background ratio
    pixels = list(img.getdata())
    total = len(pixels)
    green_count = sum(
        1 for r, g, b in pixels
        if g > 180 and r < 100 and b < 100
    )
    green_ratio = green_count / total if total else 0

    if green_ratio < MIN_GREEN_RATIO:
        issues.append(f"low_green_bg_{green_ratio:.2%}")

    # Check if image is mostly blank
    avg_r = sum(p[0] for p in pixels) / total
    avg_g = sum(p[1] for p in pixels) / total
    avg_b = sum(p[2] for p in pixels) / total
    if avg_r > 240 and avg_g > 240 and avg_b > 240:
        issues.append("mostly_white")
    if avg_r < 15 and avg_g < 15 and avg_b < 15:
        issues.append("mostly_black")

    return {
        "valid": len(issues) == 0,
        "width": w,
        "height": h,
        "green_ratio": round(green_ratio, 4),
        "issues": issues,
    }


async def validate_and_save(
    image_url: str,
    angle: str,
    attempt: int = 1,
) -> dict:
    """Download image, run basic checks, save to local disk for AI agent review.

    Returns:
        {
            "downloaded": bool,
            "local_path": str | None  (absolute path for view_file)
            "basic": {...basic check results...},
        }
    """
    image_bytes = await download_image(image_url)
    if not image_bytes:
        return {
            "downloaded": False,
            "local_path": None,
            "basic": {"valid": False, "issues": ["download_failed"]},
        }

    # Basic pixel checks
    basic = basic_checks(image_bytes)

    # Save to local disk regardless (so AI agent can see even "failed" images)
    local_path = save_image(image_bytes, angle, attempt)

    return {
        "downloaded": True,
        "local_path": str(local_path),
        "basic": basic,
    }

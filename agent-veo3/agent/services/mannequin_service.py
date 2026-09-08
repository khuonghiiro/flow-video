"""Mannequin Reference Service for Flow Character Generation Pipeline.

Manages male and female anatomical mannequin guide images across 5 standard angles:
0° (Front), 45° (3/4 Front-Left), 90° (Side Profile), 135° (3/4 Rear), 180° (Full Back).

Uploads mannequin guides to Google Flow projects to provide dual-reference (Identity + Pose)
for accurate angle rotation and proportional consistency.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("flow_agent.mannequin")

# Default search directories for mannequin assets
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]  # AI-Render-Video root
PUBLIC_MANNEQUIN_DIR = WORKSPACE_ROOT / "public" / "mannequins"
POSE_GUIDES_DIR = WORKSPACE_ROOT / "agent-veo3" / "output" / "pose-guides"

# Cache for uploaded mannequin media IDs: {(project_id, gender, angle): media_id}
_MANNEQUIN_MEDIA_CACHE: Dict[Tuple[str, str, str], str] = {}


def normalize_gender(gender_raw: Optional[str]) -> str:
    """Normalize gender input string to 'male' or 'female'."""
    if not gender_raw:
        return "female"
    g = gender_raw.strip().lower()
    if any(k in g for k in ["female", "nu", "nữ", "girl", "woman", "lady"]):
        return "female"
    if any(k in g for k in ["male", "nam", "boy", "man"]):
        return "male"
    return "female"


def normalize_angle(angle_raw: Any) -> str:
    """Normalize angle representation to '0', '45', '90', '135', '180'."""
    val = str(angle_raw).replace("°", "").strip()
    if val in ["0", "45", "90", "135", "180"]:
        return val
    try:
        deg = int(val)
        return str(deg)
    except ValueError:
        return "0"


def get_mannequin_path(gender: str, angle: str) -> str:
    """Locate local image file for given gender and angle.

    Searches public/mannequins first, then agent-veo3/output/pose-guides.
    Supports both .png and .jpg extensions.
    """
    g = normalize_gender(gender)
    a = normalize_angle(angle)

    search_dirs = [
        PUBLIC_MANNEQUIN_DIR / g,
        POSE_GUIDES_DIR / g,
        PUBLIC_MANNEQUIN_DIR,
        POSE_GUIDES_DIR,
    ]

    for d in search_dirs:
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            candidate = d / f"angle_{a}{ext}"
            if candidate.is_file():
                return str(candidate.resolve())

    # Fallback to legacy naming if exists
    legacy_file = POSE_GUIDES_DIR / f"pose_guide_{a}.jpg"
    if legacy_file.is_file():
        return str(legacy_file.resolve())

    raise FileNotFoundError(
        f"Mannequin reference image not found for gender='{g}', angle='{a}'. "
        f"Checked directories: {[str(d) for d in search_dirs]}"
    )


def get_mannequin_base64(gender: str, angle: str) -> Tuple[str, str]:
    """Read mannequin image and return (base64_encoded_str, mime_type)."""
    file_path = get_mannequin_path(gender, angle)
    mime, _ = mimetypes.guess_type(file_path)
    if not mime:
        mime = "image/png" if file_path.endswith(".png") else "image/jpeg"

    with open(file_path, "rb") as f:
        data = f.read()

    b64 = base64.b64encode(data).decode("utf-8")
    return b64, mime


async def upload_mannequin_reference(
    client: Any,
    project_id: str,
    gender: str,
    angle: str,
    force_reupload: bool = False,
) -> Optional[str]:
    """Upload mannequin reference image to Google Flow for given project.

    Returns media_id string or None if upload failed.
    """
    g = normalize_gender(gender)
    a = normalize_angle(angle)
    cache_key = (project_id, g, a)

    if not force_reupload and cache_key in _MANNEQUIN_MEDIA_CACHE:
        cached_id = _MANNEQUIN_MEDIA_CACHE[cache_key]
        logger.info("Using cached mannequin media_id for %s angle %s: %s", g, a, cached_id[:8])
        return cached_id

    try:
        b64, mime = get_mannequin_base64(g, a)
        file_name = f"mannequin_{g}_angle_{a}.png"
        logger.info("Uploading mannequin guide to Flow project %s (%s, angle %s)...", project_id[:8], g, a)

        result = await client.upload_image(
            image_base64=b64,
            mime_type=mime,
            project_id=project_id,
            file_name=file_name,
        )

        media_id = result.get("_mediaId")
        if not media_id:
            media = result.get("data", {}).get("media", {})
            if isinstance(media, dict):
                media_id = media.get("name")

        if media_id:
            _MANNEQUIN_MEDIA_CACHE[cache_key] = media_id
            logger.info("Successfully uploaded mannequin guide (%s %s°): media_id=%s", g, a, media_id[:8])
            return media_id

        logger.warning("Upload mannequin returned no media_id: %s", result)
        return None
    except Exception as e:
        logger.error("Failed to upload mannequin reference for %s angle %s: %s", g, a, e)
        return None


async def ensure_all_mannequins_for_project(
    client: Any,
    project_id: str,
    gender: str,
) -> Dict[str, Optional[str]]:
    """Batch upload/ensure mannequin media IDs for all 5 angles (0, 45, 90, 135, 180).

    Returns a dict mapping angle -> media_id.
    """
    results: Dict[str, Optional[str]] = {}
    for ang in ["0", "45", "90", "135", "180"]:
        mid = await upload_mannequin_reference(client, project_id, gender, ang)
        results[ang] = mid
    return results

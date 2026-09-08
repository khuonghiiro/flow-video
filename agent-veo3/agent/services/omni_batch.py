"""Omni Flash Batchexecute Service (Abra Models).

Implements Google Flow's batchexecute transport for Gemini Omni Flash (Abra),
providing Text-to-Video, Image-to-Video, and Reference-to-Video generation
via RPC YhhmEf, status tracking via jwpduf, and asset resolution via as29s.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from agent.services import flow_batch as fb

logger = logging.getLogger("omni_batch")

RPC_GEN_OMNI = "YhhmEf"
RPC_OPERATION = "jwpduf"
RPC_MEDIA = "as29s"
CAPTCHA_VIDEO = "VIDEO_GENERATION"
SURFACE_ID = 22

OMNI_VALID_DURATIONS = (4, 6, 8, 10)
OMNI_VALID_QUALITIES = ("360p", "720p", "1080p")


def resolve_omni_model(
    has_image: bool = False,
    is_ref: bool = False,
    duration_s: int = 4,
    quality: str = "720p",
) -> tuple[str, int]:
    """Resolve model key and resolution code for Omni Flash (Abra).

    Returns:
        (model_key, resolution_code)
        e.g. ("abra_t2v_4s", 6) for 720p 4s T2V
             ("abra_t2v_6s_360p", 4) for 360p 6s T2V
             ("abra_i2v_4s", 6) for 720p 4s I2V
    """
    dur = duration_s if duration_s in OMNI_VALID_DURATIONS else 4
    qual = quality.lower().strip() if quality else "720p"

    if is_ref:
        prefix = "abra_r2v"
    elif has_image:
        prefix = "abra_i2v"
    else:
        prefix = "abra_t2v"

    if qual == "360p":
        model_key = f"{prefix}_{dur}s_360p"
        res_code = 4
    elif qual == "1080p":
        model_key = f"{prefix}_{dur}s"
        res_code = 7
    else:  # 720p default
        model_key = f"{prefix}_{dur}s"
        res_code = 6

    return model_key, res_code


def resolve_omni_aspect(aspect_ratio: Any) -> int:
    """Resolve aspect ratio integer: 1 for portrait (9:16), 2 for landscape (16:9)."""
    if isinstance(aspect_ratio, int) and aspect_ratio in (1, 2):
        return aspect_ratio
    as_str = str(aspect_ratio).upper()
    if "LANDSCAPE" in as_str or "16:9" in as_str or "HORIZONTAL" in as_str:
        return 2
    return 1  # default PORTRAIT 9:16


def build_omni_request(
    prompt: str,
    project_id: str,
    start_image_media_id: Optional[str] = None,
    end_image_media_id: Optional[str] = None,
    reference_media_ids: Optional[list[str]] = None,
    duration_s: int = 4,
    quality: str = "720p",
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    count: int = 1,
) -> tuple[str, str]:
    """Build the f.req batchexecute payload string for RPC YhhmEf.

    Returns:
        (envelope_str, model_key)
    """
    has_image = bool(start_image_media_id)
    is_ref = bool(reference_media_ids)
    model_key, res_code = resolve_omni_model(
        has_image=has_image,
        is_ref=is_ref,
        duration_s=duration_s,
        quality=quality,
    )
    aspect_int = resolve_omni_aspect(aspect_ratio)

    items = []
    effective_count = max(1, min(count, 4))
    for _ in range(effective_count):
        u1 = fb._client_uuid()
        u2 = fb._client_uuid()
        if start_image_media_id:
            # Image-to-Video slot format
            item = [
                [None, None, [[[prompt]]]],
                model_key,
                aspect_int,
                None,
                [None, start_image_media_id, None, None, None, fb.FULL_FRAME_CROP],
                [None, None, None, None, u1, u2],
                None,
                [res_code],
            ]
        else:
            # Text-to-Video slot format
            item = [
                [None, None, [[[prompt]]]],
                model_key,
                aspect_int,
                None,
                [None, None, None, None, u1, u2],
                None,
                None,
                [res_code],
            ]
        items.append(item)

    context = [
        None,
        SURFACE_ID,
        None,
        None,
        None,
        project_id,
        None,
        None,
        None,
        None,
        [fb.CAPTCHA_SLOT, 1],
    ]
    batch_uuid = fb._client_uuid()
    inner = [items, context, [batch_uuid, 1]]

    return fb.build_envelope(RPC_GEN_OMNI, inner), model_key


def parse_omni_submit_response(payload: Any) -> list[dict]:
    """Parse the YhhmEf RPC response into structured asset records.

    Each returned item has:
        - node_id: graph asset node ID (used for project rename)
        - media_id: operation / media ID (used for status check & download)
        - project_id: Google Flow project UUID
        - title: asset title
    """
    results = []
    if not isinstance(payload, list) or len(payload) < 3:
        return results

    node_records = payload[2] if isinstance(payload[2], list) else []
    media_records = payload[3] if len(payload) > 3 and isinstance(payload[3], list) else []

    for i, node in enumerate(node_records):
        if not isinstance(node, list) or len(node) < 4:
            continue
        node_id = str(node[0])
        detail = node[3] if isinstance(node[3], list) else []
        title = detail[0] if len(detail) > 0 and isinstance(detail[0], str) else ""
        media_id = detail[4] if len(detail) > 4 and isinstance(detail[4], str) else ""
        proj_id = str(node[4]) if len(node) > 4 and node[4] else ""

        if not media_id and i < len(media_records) and isinstance(media_records[i], list):
            media_id = str(media_records[i][0])
            if not proj_id and len(media_records[i]) > 1:
                proj_id = str(media_records[i][1])

        if media_id:
            results.append({
                "node_id": node_id,
                "media_id": media_id,
                "project_id": proj_id,
                "title": title,
                "status": "PROCESSING",
            })

    return results


async def generate_omni_flash_video(
    client,
    prompt: str,
    project_id: str,
    start_image_media_id: Optional[str] = None,
    end_image_media_id: Optional[str] = None,
    reference_media_ids: Optional[list[str]] = None,
    duration_s: int = 4,
    quality: str = "720p",
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
    count: int = 1,
) -> dict:
    """Submit an Omni Flash (Abra) video generation job via YhhmEf batchexecute RPC."""
    freq, model_key = build_omni_request(
        prompt=prompt,
        project_id=project_id,
        start_image_media_id=start_image_media_id,
        end_image_media_id=end_image_media_id,
        reference_media_ids=reference_media_ids,
        duration_s=duration_s,
        quality=quality,
        aspect_ratio=aspect_ratio,
        count=count,
    )
    logger.info(
        "Submitting Omni Flash video generation (%s, dur=%ss, qual=%s, count=%d) on project %s",
        model_key, duration_s, quality, count, project_id[:8]
    )
    payload = await client._batch_payload(
        RPC_GEN_OMNI,
        freq,
        CAPTCHA_VIDEO,
        timeout=120,
    )
    assets = parse_omni_submit_response(payload)
    if not assets:
        raise fb.FlowBatchError("Omni video generation returned no valid asset records")

    for a in assets:
        if hasattr(client, "_remember_operation"):
            client._remember_operation(a["media_id"], project_id)

    return {
        "status": 200,
        "data": {
            "model_key": model_key,
            "operations": [{"operation": {"name": a["media_id"], "node_id": a["node_id"]}} for a in assets],
            "workflows": [
                {
                    "name": a["node_id"],
                    "primaryMediaId": a["media_id"],
                    "projectId": a["project_id"],
                    "title": a["title"],
                }
                for a in assets
            ],
            "assets": assets,
        },
    }


async def check_omni_media_status(client, media_id: str) -> dict:
    """Check status of an Omni generation via as29s & jwpduf.

    Returns:
        {"status": "PROCESSING" | "COMPLETED" | "FAILED", "video_url": str | None, "media_id": str}
    """
    # 1. Check direct media resolution via as29s (completed signed CDN URLs)
    try:
        freq_media = fb.media_request(media_id)
        media_payload = await client._batch_payload(RPC_MEDIA, freq_media, timeout=20)
        urls = fb.read_media_urls(media_payload, media_id)
        if urls.video:
            return {
                "status": "COMPLETED",
                "video_url": urls.video,
                "image_url": urls.image,
                "media_id": media_id,
            }
    except Exception as exc:
        logger.debug("as29s poll for %s: %s", media_id, exc)

    # 2. Check operation status via jwpduf
    try:
        freq_op = fb.operation_request(media_id)
        op_payload = await client._batch_payload(RPC_OPERATION, freq_op, timeout=20)
        # Scan for error or status code
        for node in fb._walk_lists(op_payload):
            if len(node) >= 4 and node[0] == media_id:
                err = fb.read_operation_error(node)
                if err and "not found" not in err.lower():
                    return {"status": "FAILED", "error": err, "media_id": media_id}
                return {"status": "PROCESSING", "media_id": media_id}
    except Exception as exc:
        logger.debug("jwpduf poll for %s: %s", media_id, exc)

    return {"status": "PROCESSING", "media_id": media_id}

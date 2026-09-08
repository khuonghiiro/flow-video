"""
Helper utilities and payload builders for FlowClient.
Keeps flow_client.py concise, modular, and strictly under file size limits.
"""
import time
from typing import Optional


def should_failover(result: dict) -> bool:
    """Return true for profile-local failures that another tab can solve."""
    message = str(result.get("error") or result.get("data") or "").lower()
    return any(marker in message for marker in (
        "no_flow_key",
        "no_flow_tab",
        "no_at_token",
        "flow_tab_discarded",
        "no current window",
        "extension not connected",
        "extension disconnected",
        "extension_switched",
        "public_error_per_model_daily_quota_reached",
        "public_error_user_quota_reached",
    ))


def get_extension_candidates(extensions: dict, active_ws, require_token: bool) -> list:
    """Return usable extensions in preferred routing order."""
    now = time.time()
    candidates = []
    for ws, session in extensions.items():
        if require_token and not session.get("flow_key"):
            continue
        recency = (
            session.get("token_captured_at")
            if require_token
            else session.get("connected_at")
        )
        candidates.append({
            "ws": ws,
            "available": session.get("unavailable_until", 0) <= now,
            "active": ws is active_ws,
            "recency": recency or 0,
        })

    candidates.sort(
        key=lambda item: (
            item["available"],
            item["active"] and item["available"],
            item["recency"],
        ),
        reverse=True,
    )
    return [item["ws"] for item in candidates]


def select_extension(extensions: dict, active_ws, require_token: bool):
    """Choose the preferred authenticated or connected extension."""
    candidates = get_extension_candidates(extensions, active_ws, require_token)
    return candidates[0] if candidates else None


def resolve_video_model_key(
    video_models: dict,
    user_paygate_tier: str,
    gen_type: str,
    aspect_ratio: str,
    duration: Optional[float] = None,
) -> Optional[str]:
    """Resolve the appropriate model key for video generation based on tier, type, duration, and aspect ratio."""
    type_cfg = video_models.get(user_paygate_tier, {}).get(gen_type, {})
    if not type_cfg and user_paygate_tier == "PAYGATE_TIER_ULTRA":
        type_cfg = video_models.get("PAYGATE_TIER_TWO", {}).get(gen_type, {})

    model_key = None
    if gen_type == "start_end_frame_2_video" and duration is not None:
        durations_cfg = type_cfg.get("durations", {})
        dur_int = int(round(float(duration)))
        dur_key = "4" if dur_int <= 5 else ("6" if dur_int <= 7 else "8")
        dur_entry = durations_cfg.get(dur_key)
        if isinstance(dur_entry, dict):
            model_key = dur_entry.get(aspect_ratio)
        elif isinstance(dur_entry, str):
            model_key = dur_entry

    if not model_key:
        model_key = type_cfg.get(aspect_ratio)

    if not model_key:
        type_cfg_t1 = video_models.get("PAYGATE_TIER_ONE", {}).get(gen_type, {})
        model_key = type_cfg_t1.get(aspect_ratio)

    return model_key


def get_crop_coordinates(aspect_ratio: str, crop_coordinates: Optional[dict] = None) -> dict:
    """Return normalized crop coordinates for video aspect ratio."""
    if crop_coordinates:
        return crop_coordinates
    if aspect_ratio == "VIDEO_ASPECT_RATIO_LANDSCAPE":
        return {"top": 0.3430232558139535, "left": 0, "bottom": 0.6569767441860466, "right": 1}
    return {"top": 0.003875968992248007, "left": 0, "bottom": 0.9961240310077519, "right": 1}


def get_batch_crop_list(aspect_ratio: str, crop_coordinates: Optional[dict] = None) -> list:
    """Return crop list formatted for batchexecute RPC: [None, top, right, bottom]."""
    coords = get_crop_coordinates(aspect_ratio, crop_coordinates)
    return [None, coords.get("top", 0.0038759689922481244), coords.get("right", 1), coords.get("bottom", 0.9961240310077519)]


def build_status_check_body(
    operations: Optional[list[dict]] = None,
    media: Optional[list[dict]] = None,
) -> dict:
    """Build payload for check_video_status (supporting both legacy operations and workflow media)."""
    if media:
        return {"media": media}
    if operations and any(
        op.get("_workflow_mode")
        or "projectId" in op
        or ("name" in op and "operation" not in op)
        for op in operations
    ):
        media_items = []
        for op in operations:
            mid = op.get("_primary_media_id") or op.get("name") or op.get("operation", {}).get("name")
            pid = op.get("projectId") or op.get("project_id", "")
            if mid:
                item = {"name": mid}
                if pid:
                    item["projectId"] = pid
                media_items.append(item)
        return {"media": media_items}
    return {"operations": operations or []}


def is_ws_error(result: dict) -> bool:
    """Check if API response via websocket returned an error."""
    return bool(result.get("error")) or (isinstance(result.get("status"), int) and result["status"] >= 400)

"""Veo 3.1 batch request builders and response parsers.

Handles the wire-protocol for three RPC families on ``flow.google.com``:

- **YhhmEf** — Text-to-Video (T2V): 0 reference images, prompt only.
- **MZZa6b** — Reference-to-Video (R2V): 1-3 reference images.
- **nprQif** — Frame-to-Frame / Interpolation (F2F): start + end images.

Each builder supports ``count`` (1–4) to create multiple videos in parallel,
matching the UI's x1/x2/x3/x4 batch generation.

Wire format discovered from captured network logs — see ``agent-veo3/logs/``.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from agent.services import flow_batch as fb

logger = logging.getLogger(__name__)

# ── RPC identifiers ──────────────────────────────────────────────────────────

RPC_GEN_T2V = "YhhmEf"
"""Text-to-Video generation. Takes 0 images — prompt only."""

RPC_GEN_R2V = "MZZa6b"
"""Reference-to-Video generation. Takes 1-3 reference images."""

RPC_GEN_F2F = "nprQif"
"""Frame-to-Frame / Interpolation. Takes start + end images."""

# ── T2V model keys ───────────────────────────────────────────────────────────

T2V_MODELS = {
    "veo_3_1_t2v_lite_4s_low_priority",
    "veo_3_1_t2v_lite_6s_low_priority",
    "veo_3_1_t2v_lite_low_priority",
}

T2V_DURATION_MAP = {
    4: "veo_3_1_t2v_lite_4s_low_priority",
    6: "veo_3_1_t2v_lite_6s_low_priority",
    8: "veo_3_1_t2v_lite_low_priority",
}

T2V_DEFAULT = "veo_3_1_t2v_lite_low_priority"


def resolve_t2v_model(duration_s: Any = 8) -> str:
    """Pick the T2V model key based on target duration (4, 6, or 8 seconds)."""
    dur = int(duration_s) if duration_s else 8
    return T2V_DURATION_MAP.get(dur, T2V_DEFAULT)


# ── F2F / Interpolation model keys ───────────────────────────────────────────

F2F_MODELS = {
    "veo_3_1_interpolation_lite_low_priority",
    "veo_3_1_interpolation_lite",
    "veo_3_1_interpolation_fast_ultra",
    "veo_3_1_i2v_s_lite_4s_fl_low_priority",
    "veo_3_1_i2v_s_lite_6s_fl_low_priority",
    "veo_3_1_i2v_s_lite_8s_fl_low_priority",
}

F2F_DURATION_MAP = {
    4: "veo_3_1_i2v_s_lite_4s_fl_low_priority",
    6: "veo_3_1_i2v_s_lite_6s_fl_low_priority",
    8: "veo_3_1_interpolation_lite_low_priority",
}

F2F_DEFAULT = "veo_3_1_interpolation_lite_low_priority"


def resolve_f2f_model(key_or_duration: Any = 8, tier: str = "") -> str:
    """Pick the accepted wire F2F model key for Veo 3.1 Lite Lower Priority (0 credits).

    Matches Google Flow batchexecute nprQif wire traffic:
    - 4s: veo_3_1_i2v_s_lite_4s_fl_low_priority
    - 6s: veo_3_1_i2v_s_lite_6s_fl_low_priority (as in 'tạo video với frame to frame - ngang.txt')
    - 8s: veo_3_1_interpolation_lite_low_priority (as in 'tạo video với frame to frame - dọc.txt')
    - Ultra: veo_3_1_interpolation_fast_ultra
    """
    if "ultra" in str(tier).lower() or (isinstance(key_or_duration, str) and "ultra" in key_or_duration.lower()):
        return "veo_3_1_interpolation_fast_ultra"
    if isinstance(key_or_duration, str):
        if key_or_duration in F2F_MODELS:
            return key_or_duration
        k = key_or_duration.lower()
        if "ultra" in k:
            return "veo_3_1_interpolation_fast_ultra"
        if "6s" in k:
            return "veo_3_1_i2v_s_lite_6s_fl_low_priority"
        if "4s" in k:
            return "veo_3_1_i2v_s_lite_4s_fl_low_priority"
        if "lite" in k or "low_priority" in k or "lower" in k:
            return F2F_DEFAULT
    if isinstance(key_or_duration, (int, float)):
        dur = int(key_or_duration)
        if dur in F2F_DURATION_MAP:
            return F2F_DURATION_MAP[dur]
    return F2F_DEFAULT


# ── R2V model keys ───────────────────────────────────────────────────────────

R2V_MODELS = {
    "veo_3_1_r2v_lite_low_priority",
    "veo_3_1_r2v_lite",
    "veo_3_1_r2v_fast_ultra",
}

R2V_DEFAULT = "veo_3_1_r2v_lite_low_priority"


def resolve_r2v_model(key: Any = None) -> str:
    """Map a model key to an accepted R2V wire name."""
    if isinstance(key, str):
        if key in R2V_MODELS:
            return key
        k = key.lower()
        if "ultra" in k:
            return "veo_3_1_r2v_fast_ultra"
        if "lite_low" in k or "low_priority" in k:
            return R2V_DEFAULT
        if "lite" in k:
            return "veo_3_1_r2v_lite"
    return R2V_DEFAULT


# ── T2V request builder (YhhmEf) ────────────────────────────────────────────

def build_t2v_request(
    prompt: str,
    project_id: str,
    aspect: Any = "VIDEO_ASPECT_RATIO_LANDSCAPE",
    model: str = T2V_DEFAULT,
    count: int = 1,
) -> str:
    """Build a Text-to-Video request envelope for RPC ``YhhmEf``.

    T2V items have 5 fields::

        item[0] = [null, null, [[[prompt]]]]   # prompt block
        item[1] = model_key                     # model
        item[2] = aspect_int                    # 1=portrait, 2=landscape
        item[3] = null
        item[4] = [null,null,null,null, U1, U2] # client tracking UUIDs
    """
    asp_val = fb.resolve_video_aspect(aspect)
    items = []
    for _ in range(max(1, min(count, 4))):
        items.append([
            [None, None, [[[prompt]]]],
            model,
            asp_val,
            None,
            [None, None, None, None, fb._client_uuid(), fb._client_uuid()],
        ])
    inner = [items, fb._context(project_id), [fb._client_uuid(), 1]]
    return fb.build_envelope(RPC_GEN_T2V, inner)


# ── R2V request builder (MZZa6b) ────────────────────────────────────────────

def build_r2v_request(
    prompt: str,
    project_id: str,
    reference_media_ids: Optional[list[str]] = None,
    aspect: Any = "VIDEO_ASPECT_RATIO_LANDSCAPE",
    model: str = R2V_DEFAULT,
    count: int = 1,
) -> str:
    """Build a Reference-to-Video request envelope for RPC ``MZZa6b``.

    R2V items have 6 fields::

        item[0] = [null, null, [[[prompt]]]]        # prompt block
        item[1] = [[null, ref_id_1], [null, ref_id_2]]  # reference images
        item[2] = model_key                          # model
        item[3] = aspect_int                         # 1=portrait, 2=landscape
        item[4] = null
        item[5] = [null,null,null,null, U1, U2]      # client tracking UUIDs
    """
    refs = reference_media_ids or []
    ref_list = [[None, mid] for mid in refs[:3] if mid]
    asp_val = fb.resolve_video_aspect(aspect)
    resolved_model = resolve_r2v_model(model)

    items = []
    for _ in range(max(1, min(count, 4))):
        items.append([
            [None, None, [[[prompt]]]],
            ref_list,
            resolved_model,
            asp_val,
            None,
            [None, None, None, None, fb._client_uuid(), fb._client_uuid()],
        ])
    inner = [items, fb._context(project_id), [fb._client_uuid(), 1]]
    return fb.build_envelope(RPC_GEN_R2V, inner)


# ── F2F / Interpolation request builder (nprQif) ────────────────────────────

def build_f2f_request(
    prompt: str,
    project_id: str,
    start_media_id: str,
    end_media_id: str,
    crop: Optional[list] = None,
    aspect: Any = "VIDEO_ASPECT_RATIO_LANDSCAPE",
    model: str = F2F_DEFAULT,
    count: int = 1,
) -> str:
    """Build a Frame-to-Frame interpolation request for RPC ``nprQif``.

    F2F items have 7 fields::

        item[0] = [null, null, [[[prompt]]]]                        # prompt
        item[1] = model_key                                          # model
        item[2] = aspect_int                                         # 1|2
        item[3] = null
        item[4] = [null, start_id, null, null, null, crop_box]      # start frame
        item[5] = [null, end_id, null, null, null, crop_box]        # end frame
        item[6] = [null, null, null, null, U1, U2]                  # UUIDs
    """
    if not end_media_id and start_media_id:
        return build_r2v_request(
            prompt=prompt,
            project_id=project_id,
            reference_media_ids=[start_media_id],
            aspect=aspect,
            model=resolve_r2v_model(model),
            count=count,
        )

    crop_val = getattr(fb, "FULL_FRAME_CROP", [None, 0.0038759689922481244, 1, 0.9961240310077519]) if crop is None else crop
    asp_val = fb.resolve_video_aspect(aspect) if hasattr(fb, "resolve_video_aspect") else 2
    resolved_model = resolve_f2f_model(model)

    items = []
    for _ in range(max(1, min(count, 4))):
        items.append([
            [None, None, [[[prompt]]]],
            resolved_model,
            asp_val,
            None,
            [None, start_media_id, None, None, None, crop_val],
            [None, end_media_id, None, None, None, crop_val],
            [None, None, None, None, fb._client_uuid(), fb._client_uuid()],
        ])
    inner = [items, fb._context(project_id), [fb._client_uuid(), 1]]
    return fb.build_envelope(RPC_GEN_F2F, inner)


# ── Multi-operation response parsers ─────────────────────────────────────────

def _find_operation_records(payload: Any) -> list:
    """Locate operation records in the response payload.

    Response structure (shared across YhhmEf, MZZa6b, nprQif)::

        parsedChunk[2] = nodeRecords[]       # asset nodes
        parsedChunk[3] = operationRecords[]  # operation details
    """
    if not isinstance(payload, list):
        return []

    # Prefer payload[3] (used by nprQif interpolation)
    if len(payload) > 3 and isinstance(payload[3], list) and payload[3]:
        cand = payload[3][0]
        if isinstance(cand, list) and len(cand) >= 4 and isinstance(cand[3], str):
            return payload[3]

    # Fall back to payload[2] (used by YhhmEf, MZZa6b, jwpduf)
    if len(payload) > 2 and isinstance(payload[2], list) and payload[2]:
        cand = payload[2][0]
        if isinstance(cand, list) and len(cand) >= 4:
            return payload[2]

    return []


def read_all_operations(payload: Any) -> list[fb.Operation]:
    """Parse ALL operations from a batch response (supports count > 1).

    Returns a list of ``Operation`` objects, one per generated video.
    """
    records = _find_operation_records(payload)
    if not records:
        raise fb.FlowBatchError("operation payload carried no records")

    operations = []
    for record in records:
        if not isinstance(record, list) or len(record) < 1:
            continue
        op_id = record[0]
        proj_id = record[1] if len(record) > 1 else None
        status = record[3] if len(record) > 3 and isinstance(record[3], str) else None

        # Check if this is a node record: [node_id, null, null, [title, ts, null, null, op_id, ...], proj_id]
        detail = record[3] if len(record) > 3 else None
        if isinstance(detail, list) and len(detail) > 4 and isinstance(detail[4], str) and detail[4]:
            op_id = detail[4]
            status = "MEDIA_GENERATION_STATUS_PENDING"
            if len(record) > 4 and isinstance(record[4], str):
                proj_id = record[4]

        if not isinstance(op_id, str) or not op_id:
            continue
        operations.append(fb.Operation(
            operation_id=op_id,
            project_id=proj_id,
            status=status,
            error=fb.read_operation_error(record) if len(record) > 5 else None,
        ))

    if not operations:
        raise fb.FlowBatchError("no valid operations found in response")
    return operations


def read_first_operation(payload: Any) -> fb.Operation:
    """Parse the first operation from a batch response (backward compatible)."""
    return read_all_operations(payload)[0]


def _find_node_records(payload: Any) -> list:
    """Locate asset/node records in ``parsedChunk[2]``.

    Each node: ``[node_id, null, null, [title, ts, null, null, media_id, batch_uuid, done_ts], proj_id]``
    """
    if isinstance(payload, list) and len(payload) > 2 and isinstance(payload[2], list):
        for item in payload[2]:
            if isinstance(item, list) and len(item) >= 5:
                detail = item[3] if len(item) > 3 else None
                if isinstance(detail, list) and len(detail) > 4:
                    return payload[2]
    return []


def read_all_assets(payload: Any) -> list[dict]:
    """Parse all asset/node records from the response.

    Returns list of ``{node_id, media_id, project_id, title}`` dicts.
    """
    records = _find_node_records(payload)
    assets = []
    for record in records:
        if not isinstance(record, list) or len(record) < 4:
            continue
        detail = record[3]
        if not isinstance(detail, list) or len(detail) <= 4:
            continue
        assets.append({
            "node_id": record[0],
            "media_id": detail[4] if len(detail) > 4 else None,
            "project_id": record[4] if len(record) > 4 else None,
            "title": detail[0] if detail else None,
        })
    return assets


def build_multi_operation_request(operation_ids: list[str]) -> str:
    """Build a polling request for multiple operation IDs at once.

    Wire format: ``[null, null, [[op_id_1], [op_id_2], ...]]``
    """
    op_list = [[op_id] for op_id in operation_ids]
    return fb.build_envelope(fb.RPC_OPERATION, [None, None, op_list])

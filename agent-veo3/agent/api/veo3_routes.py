"""Veo3 API Routes - Additional endpoints extending FlowKit core.

Houses endpoints for:
- Skill Tree pipeline automation (/flow/pipeline/*)
- Extension coordination & browser automation
- Request mass cancellation (/requests/cancel-all)
- Enhanced video generation supporting duration, crop, and bg notifications
"""
import asyncio
import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.services.flow_client import get_flow_client
from agent.services.skill_tree_pipeline import (
    create_pipeline,
    get_pipeline,
    list_pipelines,
)

logger = logging.getLogger("veo3_routes")

flow_veo3_router = APIRouter(prefix="/flow", tags=["flow_extensions"])
requests_veo3_router = APIRouter(prefix="/requests", tags=["requests_extensions"])


class EnhancedGenerateImageRequest(BaseModel):
    prompt: str
    project_id: Optional[str] = ""
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    character_media_ids: Optional[list[str]] = None
    title: Optional[str] = None
    display_name: Optional[str] = None


class EnhancedGenerateVideoRequest(BaseModel):
    start_image_media_id: Optional[str] = ""
    prompt: str
    project_id: str = ""
    scene_id: str = ""
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    end_image_media_id: Optional[str] = None
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    duration: Optional[float] = None
    crop_coordinates: Optional[dict] = None
    model_family: Literal["veo", "omni_flash"] = "veo"
    duration_s: int = 4
    quality: str = "720p"
    count: int = 1
    title: Optional[str] = None
    display_name: Optional[str] = None


class EnhancedGenerateVideoRefsRequest(BaseModel):
    reference_media_ids: list[str]
    prompt: str
    project_id: str = ""
    scene_id: str = ""
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    model_family: Literal["veo", "omni_flash"] = "veo"
    duration_s: int = 8


class StartPipelineRequest(BaseModel):
    project_id: str = ""
    customizer: Optional[dict] = None
    actions: Optional[list[str]] = None


class CreateFlowProjectRequest(BaseModel):
    title: str = "New Project"


class RenameFlowProjectRequest(BaseModel):
    project_id: str
    title: str


class RenameAssetRequest(BaseModel):
    asset_id: str
    name: str = ""
    title: str = ""
    project_id: Optional[str] = ""


async def _get_or_detect_project_id(client, project_id: str = "") -> str:
    """Return explicit project_id, detect active project from extension tabs, or fall back to pinned Flow project."""
    if project_id:
        return project_id
    try:
        details = await client._send("get_status", {}, timeout=5)
        for t in details.get("tabs", []):
            u = t.get("url", "")
            if "/project/" in u:
                return u.split("/project/")[1].split("/")[0].split("?")[0]
    except Exception:
        pass
    if hasattr(client, "flow_project_id"):
        fb = client.flow_project_id()
        if fb:
            return str(fb)
    from agent.config import FLOW_PROJECT_ID
    return FLOW_PROJECT_ID or project_id


# ─── Enhanced Generation Endpoints ────────────────────────────────────

@flow_veo3_router.post("/generate-image")
async def generate_image_enhanced(body: EnhancedGenerateImageRequest):
    """Generate image with automatic project detection and fallback."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    pid = await _get_or_detect_project_id(client, body.project_id or "")
    payload = body.model_dump()
    target_name = payload.pop("display_name", None) or payload.pop("title", None)
    payload["project_id"] = pid
    result = await client.generate_images(**payload)
    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))

    data = result.get("data", result)
    if target_name and hasattr(client, "rename_asset"):
        try:
            m_list = data.get("media", [])
            mid = (m_list[0].get("name") or m_list[0].get("id")) if m_list else None
            if mid:
                ren_res = await client.rename_asset(mid, target_name, pid)
                if isinstance(data, dict):
                    data["rename_result"] = ren_res
        except Exception as ren_err:
            logger.warning("Auto-rename for generated image failed: %s", ren_err)

    return data


@flow_veo3_router.post("/generate-video")
async def generate_video_enhanced(body: EnhancedGenerateVideoRequest):
    """Enhanced direct video generation with duration, crop, and bg poller."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")

    body.project_id = await _get_or_detect_project_id(client, body.project_id)
    dur_s = int(body.duration) if body.duration is not None else body.duration_s

    if body.model_family == "omni_flash":
        from agent.services.omni_batch import generate_omni_flash_video
        try:
            result = await generate_omni_flash_video(
                client=client,
                prompt=body.prompt,
                project_id=body.project_id,
                start_image_media_id=body.start_image_media_id or None,
                end_image_media_id=body.end_image_media_id or None,
                duration_s=dur_s,
                quality=body.quality,
                aspect_ratio=body.aspect_ratio,
                count=body.count,
            )
        except Exception as exc:
            logger.error("Omni Flash video generation error: %s", exc, exc_info=True)
            raise HTTPException(502, f"Omni Flash generation error: {exc}") from exc
    else:
        if not body.start_image_media_id:
            raise HTTPException(
                400,
                "Veo requires start_image_media_id. For Text-to-Video, set model_family='omni_flash'.",
            )
        result = await client.generate_video(
            start_image_media_id=body.start_image_media_id,
            prompt=body.prompt,
            project_id=body.project_id,
            scene_id=body.scene_id,
            aspect_ratio=body.aspect_ratio,
            end_image_media_id=body.end_image_media_id,
            user_paygate_tier=body.user_paygate_tier,
            duration=float(dur_s),
            crop_coordinates=body.crop_coordinates,
        )

    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))

    req_id = result.get("_req_id", "")
    data = result.get("data", result)
    target_name = body.display_name or body.title

    if target_name and hasattr(client, "rename_asset"):
        try:
            assets = data.get("assets", [])
            ops = data.get("operations", [])
            wfs = data.get("workflows", [])
            target_id = None
            if assets and isinstance(assets, list):
                target_id = assets[0].get("node_id") or assets[0].get("media_id")
            elif ops and isinstance(ops, list):
                target_id = ops[0].get("operation", {}).get("node_id") or ops[0].get("operation", {}).get("name")
            elif wfs and isinstance(wfs, list):
                target_id = wfs[0].get("name") or wfs[0].get("primaryMediaId")

            if target_id:
                ren_res = await client.rename_asset(target_id, target_name, body.project_id)
                if isinstance(data, dict):
                    data["rename_result"] = ren_res
        except Exception as ren_err:
            logger.warning("Auto-rename for generated video failed: %s", ren_err)

    asyncio.create_task(bg_poll_and_notify_video(
        client, data, req_id, body.project_id, model_family=body.model_family
    ))
    return data


@flow_veo3_router.post("/generate-video-refs")
async def generate_video_refs_enhanced(body: EnhancedGenerateVideoRefsRequest):
    """Enhanced R2V video generation with background notification."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")

    body.project_id = await _get_or_detect_project_id(client, body.project_id)

    result = await client.generate_video_from_references(
        reference_media_ids=body.reference_media_ids,
        prompt=body.prompt,
        project_id=body.project_id,
        scene_id=body.scene_id,
        aspect_ratio=body.aspect_ratio,
        user_paygate_tier=body.user_paygate_tier,
    )

    if result.get("error") or (isinstance(result.get("status"), int) and result["status"] >= 400):
        raise HTTPException(result.get("status", 502), result.get("error", result.get("data")))

    req_id = result.get("_req_id", "")
    data = result.get("data", result)
    if body.model_family != "omni_flash":
        asyncio.create_task(bg_poll_and_notify_video(client, data, req_id, body.project_id))
    return data


# ─── Pipeline Endpoints ───────────────────────────────────────────────

@flow_veo3_router.post("/pipeline/start")
async def start_pipeline(body: StartPipelineRequest):
    """Start an end-to-end 3-stage Skill Tree pipeline."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")

    project_id = body.project_id
    if not project_id:
        from agent.db import crud
        projects = await crud.list_projects()
        project_id = projects[0]["id"] if projects else ""

    pipeline = create_pipeline(
        project_id=project_id,
        customizer_values=body.customizer,
        action_keys=body.actions,
    )
    asyncio.create_task(pipeline.run())
    return {
        "pipeline_id": pipeline.id,
        "status": pipeline.status,
        "stage": pipeline.stage,
        "project_id": project_id,
    }


@flow_veo3_router.get("/pipeline/status/{pipeline_id}")
async def get_pipeline_status_endpoint(pipeline_id: str):
    """Get live status, angle states, and 5-slot activity of a pipeline."""
    pipeline = get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(404, f"Pipeline '{pipeline_id}' not found")
    return pipeline.to_dict()


@flow_veo3_router.post("/pipeline/cancel/{pipeline_id}")
async def cancel_pipeline_endpoint(pipeline_id: str):
    """Cancel a running pipeline."""
    pipeline = get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(404, f"Pipeline '{pipeline_id}' not found")
    pipeline.cancel()
    return {"pipeline_id": pipeline.id, "status": "CANCELLED"}


@flow_veo3_router.get("/pipeline/list")
async def list_pipelines_endpoint():
    """List all registered pipelines in memory."""
    return list_pipelines()


# ─── Extension & Browser Bridge Endpoints ─────────────────────────────

@flow_veo3_router.get("/extension-details")
async def extension_details():
    """Get detailed extension status including open tabs."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    return await client._send("get_status", {}, timeout=10)


@flow_veo3_router.post("/navigate-tab")
async def navigate_tab(body: dict):
    """Navigate a tab via extension."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    return await client._send("navigate_tab", body, timeout=15)


@flow_veo3_router.get("/media-redirect-url/{media_id}")
async def get_media_redirect_url(media_id: str):
    """Get signed Cloud CDN download URL for any media via Flow redirect / as29s."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    try:
        from agent.services import flow_batch as fb
        freq = fb.media_request(media_id)
        payload = await client._batch_payload(fb.RPC_MEDIA, freq, timeout=20)
        urls = fb.read_media_urls(payload, media_id)
        if urls.video or urls.image:
            return {"status": 200, "data": {"url": urls.video or urls.image, "video": urls.video, "image": urls.image}}
    except Exception as exc:
        logger.debug("as29s resolution fallback for %s: %s", media_id, exc)

    from agent.services.omni_flash import _fetch_media_url
    return await _fetch_media_url(client, media_id)


@flow_veo3_router.post("/reload-extension")
async def reload_extension():
    """Send reload command to connected Chrome extension."""
    client = get_flow_client()
    if hasattr(client, "reload_extension"):
        return await client.reload_extension()
    return await client._send("reload_extension", {}, timeout=10)


@flow_veo3_router.get("/test-captcha")
async def test_captcha_endpoint(action: str = "IMAGE_GENERATION"):
    """Test reCAPTCHA token generation via extension."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    return await client._send("solve_captcha", {"captchaAction": action}, timeout=35)


@flow_veo3_router.get("/media-urls")
async def get_all_cached_media_urls():
    """Return all cached media URLs intercepted from Google Flow."""
    client = get_flow_client()
    return getattr(client, "_recent_media_urls", {})


@flow_veo3_router.post("/fetch-blob")
async def fetch_blob_endpoint(body: dict):
    """Fetch binary blob via extension in browser context."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    url = body.get("url")
    if not url:
        raise HTTPException(400, "Missing url")
    return await client._send("fetch_blob", {"url": url}, timeout=60)


@flow_veo3_router.post("/reload-extension")
async def reload_extension_endpoint():
    """Reload the Chrome extension."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    return await client._send("reload_extension", {}, timeout=10)


@flow_veo3_router.post("/exec-tab")
async def exec_tab_endpoint(body: dict):
    """Execute JS in a Google Flow tab."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    code = body.get("code")
    if not code:
        raise HTTPException(400, "Missing code")
    return await client._send("exec_tab", {"code": code, "tabId": body.get("tab_id")}, timeout=30)


@flow_veo3_router.get("/captured-video-urls")
async def get_captured_video_urls():
    """Get video URLs captured by extension webRequest."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    res = await client._send("get_captured_video_urls", {}, timeout=10)
    return res.get("result", []) if isinstance(res, dict) else []


@flow_veo3_router.get("/captured-batches")
async def get_captured_batches():
    """Get batchexecute payloads captured by extension webRequest."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    res = await client._send("get_captured_batches", {}, timeout=10)
    return res.get("result", []) if isinstance(res, dict) else []


@flow_veo3_router.post("/project/create")
async def create_flow_project(body: CreateFlowProjectRequest):
    """Create a new project on Google Flow via jHPbke RPC."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    result = await client.create_project(body.title)
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result.get("data", result)


@flow_veo3_router.post("/project/rename")
async def rename_flow_project(body: RenameFlowProjectRequest):
    """Rename an existing project on Google Flow via o8DA4 RPC."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    if hasattr(client, "rename_project"):
        result = await client.rename_project(body.project_id, body.title)
    else:
        raise HTTPException(501, "rename_project method not implemented")
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result.get("data", result)


@flow_veo3_router.post("/asset/rename")
@flow_veo3_router.post("/image/rename")
@flow_veo3_router.post("/video/rename")
async def rename_flow_asset(body: RenameAssetRequest):
    """Rename an existing asset (image or video) on Google Flow via mYWVGd RPC."""
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")

    new_name = (body.name or body.title or "").strip()
    if not new_name:
        raise HTTPException(400, "Missing new asset name/title")

    project_id = await _get_or_detect_project_id(client, body.project_id or "")
    if not project_id:
        raise HTTPException(400, "Missing project_id")

    if hasattr(client, "rename_asset"):
        result = await client.rename_asset(body.asset_id, new_name, project_id)
    else:
        raise HTTPException(501, "rename_asset method not implemented")

    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result.get("data", result)


# ─── Queue / Request Operations ──────────────────────────────────────

@requests_veo3_router.post("/cancel-all")
async def cancel_all_requests():
    """Cancel all active (PENDING or PROCESSING) requests."""
    from agent.db import crud
    active = await crud.list_requests()
    cancelled = 0
    for r in active:
        if r.get("status") in ("PENDING", "PROCESSING"):
            await crud.update_request(r["id"], status="FAILED", error_message="Cancelled by user")
            cancelled += 1

    from agent.worker.processor import get_worker_controller
    controller = get_worker_controller()
    controller._active_ids.clear()
    controller._deferred.clear()
    controller._retry_after.clear()

    return {"status": "ok", "cancelled": cancelled}


async def bg_poll_and_notify_video(
    client, data: dict, req_id: str = "", project_id: str = "", model_family: str = "veo"
):
    """Poll video status in background and notify extension UI of completion."""
    from agent.config import VIDEO_POLL_INTERVAL

    # 1. Identify primary media ID
    assets = data.get("assets", [])
    primary_mid = ""
    if assets and isinstance(assets, list):
        primary_mid = assets[0].get("media_id", "")

    if not primary_mid:
        workflows = data.get("workflows", [])
        if workflows and isinstance(workflows, list):
            wf0 = workflows[0]
            meta = wf0.get("metadata", {})
            primary_mid = meta.get("primaryMediaId") or wf0.get("primaryMediaId", "")
            if not primary_mid and wf0.get("name"):
                primary_mid = wf0.get("name", "")

    if not primary_mid:
        ops = data.get("operations", [])
        if ops and isinstance(ops, list):
            op0 = ops[0]
            op_data = op0.get("operation", op0)
            primary_mid = op_data.get("name", "")

    if not primary_mid:
        media = data.get("media", [])
        if media and isinstance(media, list):
            primary_mid = media[0].get("name", "")

    if not primary_mid:
        return

    for _ in range(60):  # max ~10 min
        await asyncio.sleep(VIDEO_POLL_INTERVAL)
        try:
            if model_family == "omni_flash":
                from agent.services.omni_batch import check_omni_media_status
                res = await check_omni_media_status(client, primary_mid)
                st = res.get("status")
                v_url = res.get("video_url")
                if st == "COMPLETED" and v_url:
                    logger.info("BG Omni video poll complete: %s (url=%s)", primary_mid[:8], v_url[:50])
                    if hasattr(client, "notify_request_status"):
                        await client.notify_request_status(
                            req_id=req_id, media_id=primary_mid, status="COMPLETED", output_url=v_url
                        )
                    return
                elif st == "FAILED":
                    err = res.get("error", "Omni generation failed")
                    logger.warning("BG Omni video poll failed: %s: %s", primary_mid[:8], err)
                    if hasattr(client, "notify_request_status"):
                        await client.notify_request_status(
                            req_id=req_id, media_id=primary_mid, status="FAILED", output_url=""
                        )
                    return
            else:
                from agent.services import flow_batch as fb
                freq = fb.media_request(primary_mid)
                v_url = None
                try:
                    payload = await client._batch_payload(fb.RPC_MEDIA, freq, timeout=20)
                    urls = fb.read_media_urls(payload, primary_mid)
                    v_url = urls.video
                except Exception:
                    pass

                if not v_url:
                    from agent.services.omni_flash import _fetch_media_url
                    url_res = await _fetch_media_url(client, primary_mid)
                    if url_res and not url_res.get("error"):
                        v_data = url_res.get("data", {})
                        v_url = v_data.get("url", "")

                if v_url:
                    logger.info("BG video poll complete: %s (url=%s)", primary_mid[:8], v_url[:50])
                    if hasattr(client, "notify_request_status"):
                        await client.notify_request_status(
                            req_id=req_id, media_id=primary_mid, status="COMPLETED", output_url=v_url
                        )
                    return
        except Exception as exc:
            logger.debug("Background poll check error: %s", exc)

    logger.warning("Background poll timed out for video %s", primary_mid[:8])

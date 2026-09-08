"""Veo3 Extension Patcher - Non-invasive runtime patcher for FlowKit Core.

Dynamically enriches FlowKit core modules at runtime with Veo3 advanced capabilities:
- Custom 4s/6s/8s loop models and durations from models_extension.json
- FlowClient extensions (generate_video duration, crop, browser helpers, request notify)
- Operations tracking (project_id, scene_id, TRPC early URL pickup)
- Worker parser fallbacks and MV3 WebSocket heartbeat keepalive
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("extension_patcher")

_EXT_DIR = Path(__file__).resolve().parent
_MODELS_EXT_FILE = _EXT_DIR / "models_extension.json"


def _deep_merge_dict(target: dict, source: dict):
    """Recursively merge source dictionary into target dictionary."""
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            _deep_merge_dict(target[key], value)
        else:
            target[key] = value


def patch_models_and_config():
    """Merge custom video models and durations into agent.config.VIDEO_MODELS."""
    if not _MODELS_EXT_FILE.exists():
        return

    try:
        from agent.flowkit_loader import bootstrap_flowkit
        bootstrap_flowkit()
        from agent import config
        with open(_MODELS_EXT_FILE, encoding="utf-8") as f:
            ext_data = json.load(f)

        ext_video_models = ext_data.get("video_models", {})
        _deep_merge_dict(config.VIDEO_MODELS, ext_video_models)

        if "default_image_model" in ext_data and not hasattr(config, "DEFAULT_IMAGE_MODEL"):
            config.DEFAULT_IMAGE_MODEL = ext_data["default_image_model"]

        # Enable degraded fallback for chaining on batch API dynamically at runtime
        config.FLOW_ALLOW_DEGRADED = True

        logger.info("Successfully merged Veo3 custom models & durations into VIDEO_MODELS")
    except Exception as exc:
        logger.error("Failed to patch models & config: %s", exc)


def patch_db_and_crud():
    """Patch SQLite schema connection and crud methods for concurrency and upsert support."""
    try:
        from agent.flowkit_loader import bootstrap_flowkit
        bootstrap_flowkit()
        from agent.db import schema, crud

        # 1. Patch schema.get_db to enforce busy_timeout=30000
        orig_get_db = schema.get_db

        async def enhanced_get_db():
            conn = await orig_get_db()
            try:
                await conn.execute("PRAGMA busy_timeout=30000")
            except Exception:
                pass
            return conn

        schema.get_db = enhanced_get_db

        # 2. Patch crud.create_project to safely update existing project on id conflict
        orig_create_project = crud.create_project

        async def enhanced_create_project(
            name: str,
            description: str = None,
            story: str = None,
            language: str = "en",
            user_paygate_tier: str = "PAYGATE_TIER_ONE",
            id: str = None,
            material: str = None,
            allow_music: bool = False,
            allow_voice: bool = False,
        ) -> dict:
            if id:
                existing = await crud.get_project(id)
                if existing:
                    await crud.update_project(
                        id,
                        name=name,
                        description=description,
                        story=story,
                        language=language,
                        user_paygate_tier=user_paygate_tier,
                        material=material,
                        allow_music=int(allow_music),
                        allow_voice=int(allow_voice),
                    )
                    db = await schema.get_db()
                    return await crud._get_with_db(db, "project", "id", id)

            return await orig_create_project(
                name=name,
                description=description,
                story=story,
                language=language,
                user_paygate_tier=user_paygate_tier,
                id=id,
                material=material,
                allow_music=allow_music,
                allow_voice=allow_voice,
            )

        crud.create_project = enhanced_create_project
        logger.info("Successfully patched SQLite schema & crud with concurrency and upsert support")
    except Exception as exc:
        logger.warning("Failed to patch db and crud: %s", exc)


def patch_flow_client():
    """Enrich FlowClient with duration, crop coordinates, batch transport and browser actions."""
    try:
        from agent.flowkit_loader import bootstrap_flowkit
        bootstrap_flowkit()
        from agent.services.flow_client import FlowClient
        from agent.services.flow_client_helpers import (
            get_crop_coordinates,
            get_batch_crop_list,
            resolve_video_model_key,
        )
        from agent import config

        orig_generate_video = FlowClient.generate_video

        async def enhanced_generate_video(
            self,
            start_image_media_id: str,
            prompt: str,
            project_id: str,
            scene_id: str,
            aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
            end_image_media_id: str = None,
            user_paygate_tier: str = "PAYGATE_TIER_TWO",
            duration: Optional[float] = 4.0,
            crop_coordinates: Optional[dict] = None,
        ) -> dict:
            from agent.config import USE_BATCH_RPC, FLOW_ALLOW_DEGRADED
            from agent.services import flow_batch as fb
            from agent.services.flow_client import _as_pending_operation, _batch_error, _unsupported

            gen_type = "start_end_frame_2_video" if end_image_media_id else "frame_2_video"

            # ─── Flow batchexecute transport (Current path on flow.google.com) ───
            if USE_BATCH_RPC:
                if end_image_media_id:
                    if not FLOW_ALLOW_DEGRADED:
                        return {"error": _unsupported(
                            "start+end frame chaining",
                            "the new payload's end-image slot was never captured",
                        )}
                    logger.warning(
                        "Scene %s: dropping end frame %s — chaining is not on the batch path, "
                        "running plain i2v because FLOW_ALLOW_DEGRADED=1",
                        str(scene_id)[:12], end_image_media_id[:12],
                    )

                batch_model = self._batch_video_model(user_paygate_tier, gen_type, aspect_ratio)
                crop_list = get_batch_crop_list(aspect_ratio, crop_coordinates)

                logger.info(
                    "[VEO3 BATCH DISPATCH] gen_type=%s model=%s aspect=%s duration=%s end_frame=%s",
                    gen_type, batch_model, aspect_ratio, duration, bool(end_image_media_id)
                )

                try:
                    pid = self._batch_project_id(project_id)
                    freq = fb.video_request(
                        prompt, pid, start_image_media_id, crop=crop_list, aspect=aspect_ratio,
                        model=batch_model,
                    )
                    payload = await self._batch_payload(
                        fb.RPC_GEN_VIDEO, freq, fb.CAPTCHA_VIDEO, timeout=120
                    )
                    operation = fb.read_operation(payload)
                except Exception as e:
                    return _batch_error(e)

                self._remember_operation(operation.operation_id, pid)
                return {"status": 200, "data": {"operations": [_as_pending_operation(operation.operation_id)]}}

            # ─── Legacy REST transport fallback (pre-migration aisandbox-pa) ───
            model_key = resolve_video_model_key(
                config.VIDEO_MODELS, user_paygate_tier, gen_type, aspect_ratio, duration
            )
            if not model_key:
                if gen_type == "start_end_frame_2_video":
                    model_key = "veo_3_1_i2v_s_lite_4s_fl_low_priority"
                else:
                    model_key = "veo_3_1_i2v_lite_low_priority"

            logger.info(
                "[VEO3 LEGACY REST DISPATCH] gen_type=%s model_key=%s duration=%s tier=%s end_frame=%s",
                gen_type, model_key, duration, user_paygate_tier, bool(end_image_media_id)
            )

            import time
            import uuid

            crop_coords = get_crop_coordinates(aspect_ratio, crop_coordinates)
            request = {
                "outputSpec": {"resolution": "VIDEO_RESOLUTION_720P"},
                "aspectRatio": aspect_ratio,
                "seed": int(time.time()) % 10000,
                "textInput": {"structuredPrompt": {"parts": [{"text": prompt}]}},
                "videoModelKey": model_key,
                "startImage": {"mediaId": start_image_media_id, "cropCoordinates": crop_coords},
                "metadata": {"sceneId": scene_id} if scene_id else {},
            }
            if end_image_media_id:
                request["endImage"] = {"mediaId": end_image_media_id, "cropCoordinates": crop_coords}

            endpoint_key = "generate_video_start_end" if end_image_media_id else "generate_video"
            body = {
                "mediaGenerationContext": {
                    "batchId": f"{uuid.uuid4()}",
                    "audioFailurePreference": "BLOCK_SILENCED_VIDEOS",
                },
                "clientContext": self._client_context(project_id, user_paygate_tier),
                "requests": [request],
                "useV2ModelConfig": True,
            }
            from agent.services.headers import random_headers
            url = self._build_url(endpoint_key)
            return await self._send("api_request", {
                "url": url,
                "method": "POST",
                "headers": random_headers(),
                "body": body,
                "captchaAction": "VIDEO_GENERATION",
            }, timeout=60)

        FlowClient.generate_video = enhanced_generate_video

        # Add helper methods to FlowClient
        if not hasattr(FlowClient, "notify_request_status"):
            async def notify_request_status(
                self, req_id: str = "", media_id: str = "", status: str = "COMPLETED", output_url: str = ""
            ):
                msg = {"type": "update_request_log", "id": req_id, "mediaId": media_id, "status": status, "outputUrl": output_url}
                raw = json.dumps(msg)
                for ws in list(self._extensions.keys()):
                    try:
                        await ws.send(raw)
                    except Exception:
                        pass
            FlowClient.notify_request_status = notify_request_status

        if not hasattr(FlowClient, "reload_extension"):
            async def reload_extension(self) -> dict:
                for ws in list(self._extensions.keys()):
                    try:
                        await ws.send(json.dumps({"type": "reload_extension"}))
                    except Exception:
                        pass
                return {"status": "ok"}
            FlowClient.reload_extension = reload_extension

        if not hasattr(FlowClient, "fetch_blob"):
            async def fetch_blob(self, url: str) -> dict:
                return await self._send("fetch_blob", {"url": url}, timeout=60)
            FlowClient.fetch_blob = fetch_blob

        if not hasattr(FlowClient, "exec_tab"):
            async def exec_tab(self, code: str, tab_id: Optional[int] = None) -> dict:
                return await self._send("exec_tab", {"code": code, "tabId": tab_id}, timeout=30)
            FlowClient.exec_tab = exec_tab

        if not hasattr(FlowClient, "get_captured_video_urls"):
            async def get_captured_video_urls(self) -> list:
                res = await self._send("get_captured_video_urls", {}, timeout=10)
                return res.get("result", []) if isinstance(res, dict) else []
            FlowClient.get_captured_video_urls = get_captured_video_urls

        # ─── Batch RPC project creation (jHPbke) & renaming (o8DA4) ───
        orig_create_project = FlowClient.create_project

        async def enhanced_create_project(self, project_title: str, tool_name: str = "PINHOLE") -> dict:
            from agent.config import USE_BATCH_RPC
            from agent.services import flow_batch as fb
            if not USE_BATCH_RPC:
                return await orig_create_project(self, project_title, tool_name)

            title = (project_title or f"Project {int(time.time())}").strip()
            try:
                inner_create = ["projects/*", [None, [title]], [None, 22]]
                freq_create = fb.build_envelope("jHPbke", inner_create)
                payload = await self._batch_payload("jHPbke", freq_create, timeout=60)

                new_project_id = None
                if isinstance(payload, list) and len(payload) > 0:
                    new_project_id = payload[0]
                elif isinstance(payload, str):
                    new_project_id = payload

                if not new_project_id or not isinstance(new_project_id, str):
                    raise fb.FlowBatchError(f"Could not parse project ID from jHPbke response: {payload}")

                logger.info("Successfully created Flow project via jHPbke RPC: %s ('%s')", new_project_id, title)

                try:
                    inner_rename = [f"projects/{new_project_id}", [title], [["project_title"]], [None, 22]]
                    freq_rename = fb.build_envelope("o8DA4", inner_rename)
                    await self._batch_payload("o8DA4", freq_rename, timeout=30)
                    logger.info("Successfully synced project title via o8DA4 RPC: '%s'", title)
                except Exception as ren_err:
                    logger.warning("Optional project rename via o8DA4: %s", ren_err)

                self.override_flow_project_id = new_project_id
                config.FLOW_PROJECT_ID = new_project_id

                return {"status": 200, "data": {"projectId": new_project_id}}
            except Exception as e:
                logger.error("Batch project creation (jHPbke) failed: %s", e)
                pinned = self.flow_project_id()
                if pinned:
                    logger.warning("Falling back to pinned project %s", pinned)
                    return {"status": 200, "data": {"projectId": pinned}}
                return {"error": f"Failed to create Flow project: {e}"}

        FlowClient.create_project = enhanced_create_project

        async def rename_project(self, project_id: str, new_title: str) -> dict:
            from agent.services import flow_batch as fb
            pid = (project_id or self.flow_project_id() or "").strip()
            if not pid:
                return {"error": "Missing project_id"}
            title = (new_title or "").strip()
            if not title:
                return {"error": "Missing new_title"}
            try:
                inner_rename = [f"projects/{pid}", [title], [["project_title"]], [None, 22]]
                freq_rename = fb.build_envelope("o8DA4", inner_rename)
                payload = await self._batch_payload("o8DA4", freq_rename, timeout=30)
                logger.info("Successfully renamed project %s to '%s' via o8DA4", pid, title)
                return {"status": 200, "data": {"projectId": pid, "title": title, "result": payload}}
            except Exception as e:
                logger.error("Rename project (o8DA4) failed: %s", e)
                return {"error": f"Failed to rename project: {e}"}

        FlowClient.rename_project = rename_project

        async def rename_asset(self, asset_id: str, new_name: str, project_id: str = "") -> dict:
            from agent.services import flow_batch as fb
            pid = (project_id or self.flow_project_id() or "").strip()
            if not pid:
                return {"error": "Missing project_id"}
            aid = (asset_id or "").strip()
            if not aid:
                return {"error": "Missing asset_id"}
            name = (new_name or "").strip()
            if not name:
                return {"error": "Missing new_name"}
            async def _do_rename(target_id: str):
                inner = [[target_id, None, None, [name], pid], [["metadata.display_name"]]]
                freq = fb.build_envelope("mYWVGd", inner)
                return await self._batch_payload("mYWVGd", freq, timeout=30)

            try:
                try:
                    payload = await _do_rename(aid)
                except Exception as first_err:
                    # If direct aid failed, it might be a media_id. Try resolving to node opId via project listing.
                    logger.debug("Direct rename for %s failed (%s), trying project media listing lookup...", aid, first_err)
                    resolved_id = None
                    try:
                        freq_list = fb.project_media_request(pid)
                        list_payload = await self._batch_payload(fb.RPC_PROJECT_MEDIA, freq_list, timeout=30)
                        for node in fb._walk_lists(list_payload):
                            if len(node) >= 4 and isinstance(node[3], list):
                                detail = node[3]
                                if len(detail) > 4 and detail[4] == aid:
                                    resolved_id = str(node[0])
                                    break
                    except Exception as list_err:
                        logger.debug("Project listing lookup failed: %s", list_err)

                    if resolved_id:
                        logger.info("Resolved media_id %s -> asset node ID %s", aid, resolved_id)
                        aid = resolved_id
                        payload = await _do_rename(aid)
                    else:
                        raise first_err

                logger.info("Successfully renamed asset %s to '%s' via mYWVGd RPC", aid, name)

                updated_title = name
                media_id = None
                if isinstance(payload, list) and len(payload) > 3 and isinstance(payload[3], list):
                    meta_list = payload[3]
                    if len(meta_list) > 0 and isinstance(meta_list[0], str):
                        updated_title = meta_list[0]
                    if len(meta_list) > 4 and isinstance(meta_list[4], str):
                        media_id = meta_list[4]

                return {
                    "status": 200,
                    "data": {
                        "assetId": aid,
                        "displayName": updated_title,
                        "mediaId": media_id,
                        "projectId": pid,
                        "result": payload,
                    },
                }
            except Exception as e:
                logger.error("Rename asset (mYWVGd) failed: %s", e)
                return {"error": f"Failed to rename asset: {e}"}

        FlowClient.rename_asset = rename_asset

        orig_flow_project_id = FlowClient.flow_project_id

        def enhanced_flow_project_id(self, override: str | None = None) -> str:
            if override in ("new", "create", "__new__"):
                return None
            return orig_flow_project_id(self, override)

        FlowClient.flow_project_id = enhanced_flow_project_id

        logger.info("Successfully patched FlowClient with Veo3 enhancements, jHPbke/o8DA4 & mYWVGd RPCs")
    except Exception as exc:
        logger.error("Failed to patch FlowClient: %s", exc)


def patch_worker_parsing():
    """Ensure worker prioritizes generatedImage.mediaId over raw asset name."""
    try:
        from agent.worker import _parsing

        orig_extract = _parsing._extract_media_id

        def enhanced_extract(result: dict, req_type: str) -> Optional[str]:
            data = result.get("data", result)
            if req_type in (
                "GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE",
                "GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE"
            ):
                media = data.get("media", [])
                if media and isinstance(media, list):
                    item = media[0]
                    gen = item.get("image", {}).get("generatedImage", {})
                    val = gen.get("mediaId", "")
                    if val and _parsing._is_uuid(val):
                        return val
                    for url_field in ("fifeUrl", "imageUri"):
                        url = gen.get(url_field, "")
                        if url:
                            uuid_val = _parsing._extract_uuid_from_url(url)
                            if uuid_val:
                                return uuid_val
                    name = item.get("name", "")
                    if name and _parsing._is_uuid(name):
                        return name
                    return None
            return orig_extract(result, req_type)

        _parsing._extract_media_id = enhanced_extract
        logger.info("Successfully patched worker _parsing")
    except Exception as exc:
        logger.error("Failed to patch worker parsing: %s", exc)


def patch_websocket_heartbeat(app):
    """Inject 15s ping heartbeat into WebSocket route to keep Chrome MV3 alive."""
    try:
        from fastapi.routing import APIWebSocketRoute
        for route in app.routes:
            if isinstance(route, APIWebSocketRoute) and route.path == "/ws":
                orig_endpoint = route.endpoint

                async def heartbeat_endpoint(websocket):
                    heartbeat_task = None
                    async def _heartbeat():
                        try:
                            while True:
                                await asyncio.sleep(15)
                                await websocket.send(json.dumps({"type": "ping"}))
                        except Exception:
                            pass
                    try:
                        heartbeat_task = asyncio.create_task(_heartbeat())
                        await orig_endpoint(websocket)
                    finally:
                        if heartbeat_task:
                            heartbeat_task.cancel()

                route.endpoint = heartbeat_endpoint
                logger.info("Injected 15s heartbeat into /ws endpoint")
                break
    except Exception as exc:
        logger.warning("Could not patch websocket heartbeat: %s", exc)


def mount_extension_routes(app):
    """Mount Veo3 routers for flow and requests extensions, overriding upstream routes."""
    try:
        from fastapi.routing import _IncludedRouter
        from agent.api.veo3_routes import flow_veo3_router, requests_veo3_router

        # Strip shadowed routes from upstream routers
        veo3_paths = {getattr(r, "path", "") for r in flow_veo3_router.routes}
        for route in app.router.routes:
            if isinstance(route, _IncludedRouter) and route.original_router is not flow_veo3_router:
                route.original_router.routes = [
                    r for r in route.original_router.routes
                    if getattr(r, "path", "") not in veo3_paths
                ]

        # Mount with /api prefix (primary standard FlowKit convention)
        app.include_router(flow_veo3_router, prefix="/api")
        app.include_router(requests_veo3_router, prefix="/api")

        # Mount without /api prefix for convenient direct script access
        app.include_router(flow_veo3_router)
        app.include_router(requests_veo3_router)

        # Clear cached openapi schema
        app.openapi_schema = None

        logger.info("Mounted Veo3 custom routes to FastAPI application")
    except Exception as exc:
        logger.error("Failed to mount Veo3 routes: %s", exc)


def apply_all_patches(app=None):
    """One-stop bootstrap function to apply all Veo3 runtime enhancements."""
    patch_models_and_config()
    patch_db_and_crud()
    patch_flow_client()
    patch_worker_parsing()
    if app is not None:
        patch_websocket_heartbeat(app)
        mount_extension_routes(app)
    logger.info("All Veo3 patches successfully applied")

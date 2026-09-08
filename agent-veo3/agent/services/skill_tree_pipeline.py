"""Skill Tree Auto-Pipeline Orchestrator.

Manages 3 dependency stages for automated 2D Sprite generation:
Stage 1: Generate Master Base 0° Character (Root Identity)
Stage 2: Generate 4 remaining body angles (45°, 90°, 135°, 180°) using 0° as reference
Stage 3: Sliding window continuous 5-slot queue for 4s seamless loop videos with auto-retry
"""
import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional
from agent.services.flow_client import get_flow_client
from agent.services.prompt_templates import (
    DEFAULT_CUSTOMIZER_VALUES,
    ANGLE_PROMPT_TEMPLATES,
    ACTION_TEMPLATES,
    format_template,
    get_action_templates,
)
from agent.sdk.services.operations import _extract_operations, _poll_operations
from agent.services.image_validator import validate_and_save
from agent.services.mannequin_service import upload_mannequin_reference

logger = logging.getLogger(__name__)


class SkillTreePipeline:
    """Executes end-to-end skill tree generation with 5-slot sliding window."""

    def __init__(self, project_id: str, customizer_values: Optional[dict] = None,
                 action_keys: Optional[List[str]] = None):
        self.id = str(uuid.uuid4())
        self.project_id = project_id
        self.customizer = {**DEFAULT_CUSTOMIZER_VALUES, **(customizer_values or {})}
        self.action_keys = action_keys or ["walk"]
        self.user_paygate_tier = (customizer_values or {}).get("user_paygate_tier", "PAYGATE_TIER_TWO")
        self.status = "IDLE"
        self.stage = "INIT"
        self.error_message: Optional[str] = None
        self._cancelled = False

        self.angles: Dict[str, dict] = {
            "0": {"media_id": None, "url": None, "status": "PENDING"},
            "45": {"media_id": None, "url": None, "status": "PENDING"},
            "90": {"media_id": None, "url": None, "status": "PENDING"},
            "135": {"media_id": None, "url": None, "status": "PENDING"},
            "180": {"media_id": None, "url": None, "status": "PENDING"},
        }

        self.tasks: List[dict] = []
        self.slots: List[dict] = [
            {"slot": i, "task_id": None, "name": "Idle", "status": "IDLE", "elapsed_s": 0}
            for i in range(5)
        ]
        self._init_task_queue()

    def _init_task_queue(self):
        """Prepare tasks list for Stage 3 actions from all requested action_keys."""
        angle_order = ["0", "45", "90", "135", "180"]
        angle_labels = {
            "0": "0. Chinh dien", "45": "45. Nghieng trai",
            "90": "90. Nhin ngang", "135": "135. Lung phai", "180": "180. Sau lung",
        }
        action_labels = {
            "walk": "Di Bo", "idle": "Dung Yen", "run": "Chay",
            "attack": "Danh Cong", "defend": "Phong Thu",
        }

        for action_key in self.action_keys:
            templates = get_action_templates(action_key, self.customizer)
            if not templates:
                logger.warning("No templates for action '%s', skipping", action_key)
                continue
            action_label = action_labels.get(action_key, action_key.title())
            for ang in angle_order:
                raw_prompt = templates.get(ang)
                if not raw_prompt:
                    continue
                prompt_text = format_template(raw_prompt, self.customizer)
                self.tasks.append({
                    "id": str(uuid.uuid4()),
                    "type": action_key,
                    "angle": ang,
                    "name": f"{action_label} {angle_labels[ang]} (4s Loop)",
                    "prompt": prompt_text,
                    "status": "PENDING",
                    "output_url": None,
                    "retries": 0,
                    "error": None,
                })

    def to_dict(self) -> dict:
        """Return serialized snapshot for API & UI."""
        completed_count = sum(1 for t in self.tasks if t["status"] == "COMPLETED")
        total_tasks = len(self.tasks)
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "stage": self.stage,
            "angles": self.angles,
            "slots": self.slots,
            "tasks": self.tasks,
            "progress": {
                "completed": completed_count,
                "total": total_tasks,
                "percent": int((completed_count / total_tasks * 100)) if total_tasks else 0,
            },
            "error_message": self.error_message,
        }

    def cancel(self):
        """Signal pipeline to stop."""
        self._cancelled = True
        self.status = "CANCELLED"
        logger.info("Pipeline %s cancelled by user", self.id[:8])

    async def run(self):
        """Main orchestrator executing Stage 1 -> Stage 2 -> Stage 3."""
        self.status = "RUNNING"
        try:
            # Stage 1: Base Character 0°
            self.stage = "STAGE_1_BASE"
            logger.info("Pipeline %s: Starting Stage 1 (0° Base Character)", self.id[:8])
            ok = await self._generate_base_0()
            if not ok or self._cancelled:
                return

            # Stage 2: 4 Remaining Angles
            self.stage = "STAGE_2_ANGLES"
            logger.info("Pipeline %s: Starting Stage 2 (4 Angles with 0° Ref)", self.id[:8])
            ok = await self._generate_4_angles()
            if not ok or self._cancelled:
                return

            # Stage 3: Sliding Window 5-Slot Actions Queue
            self.stage = "STAGE_3_ACTIONS"
            logger.info("Pipeline %s: Starting Stage 3 (5-Slot Sliding Window Actions)", self.id[:8])
            await self._run_sliding_window_actions()

            if not self._cancelled:
                self.status = "COMPLETED"
                logger.info("Pipeline %s: Completed all stages successfully!", self.id[:8])
        except Exception as e:
            self.status = "FAILED"
            self.error_message = str(e)
            logger.exception("Pipeline %s encountered fatal error: %s", self.id[:8], e)

    async def _generate_base_0(self) -> bool:
        """Stage 1: Generate 0° Master Base with auto-retry + validation."""
        client = get_flow_client()
        prompt_0 = format_template(ANGLE_PROMPT_TEMPLATES["0"], self.customizer)
        self.angles["0"]["status"] = "GENERATING"
        retries = 0
        max_retries = 5

        while not self._cancelled and retries < max_retries:
            retries += 1
            try:
                res = await client.generate_images(
                    prompt=prompt_0,
                    project_id=self.project_id,
                    aspect_ratio="IMAGE_ASPECT_RATIO_PORTRAIT",
                    user_paygate_tier=self.user_paygate_tier,
                )
                if res.get("error"):
                    logger.warning("Stage 1 0° API error: %s, retrying... (%d/%d)", res.get("error"), retries, max_retries)
                    await asyncio.sleep(5)
                    continue
                media_id, url = self._extract_image_result(res)
                if not media_id:
                    logger.warning("Stage 1 0° empty result, retrying... (%d/%d)", retries, max_retries)
                    await asyncio.sleep(5)
                    continue

                # Validate image & save locally for AI agent review
                if url:
                    val = await validate_and_save(image_url=url, angle="0", attempt=retries)
                    self.angles["0"]["validation"] = val
                    self.angles["0"]["local_path"] = val.get("local_path")
                    if not val.get("downloaded") or not val.get("basic", {}).get("valid", True):
                        issues = val.get("basic", {}).get("issues", [])
                        logger.warning(
                            "Stage 1 0° basic check failed (issues=%s), retrying... (%d/%d)",
                            issues, retries, max_retries,
                        )
                        await asyncio.sleep(5)
                        continue
                    logger.info("Stage 1 0° saved to %s (green_ratio=%s)", val.get("local_path"), val.get("basic", {}).get("green_ratio"))

                self.angles["0"]["media_id"] = media_id
                self.angles["0"]["url"] = url
                self.angles["0"]["status"] = "COMPLETED"
                logger.info("Stage 1 success: 0° media_id=%s", media_id[:8])
                return True
            except Exception as e:
                logger.warning("Stage 1 0° failed: %s, retrying... (%d/%d)", e, retries, max_retries)
                await asyncio.sleep(5)

        logger.error("Stage 1 0° exhausted %d retries", max_retries)
        return False

    async def _generate_single_angle(self, angle_key: str, ref_media_id: str):
        """Generate one angle image using Dual-Ref (0° identity + mannequin angle guide) with auto-retry."""
        client = get_flow_client()
        raw_tmpl = ANGLE_PROMPT_TEMPLATES[angle_key]
        prompt = format_template(raw_tmpl, self.customizer)
        self.angles[angle_key]["status"] = "GENERATING"
        ref_url = self.angles["0"].get("url")  # 0° image URL for comparison
        retries = 0
        max_retries = 5

        # Dual-Ref: Character Identity + Mannequin Pose Guide for target angle & gender
        gender = self.customizer.get("gender", "female")
        mannequin_mid = await upload_mannequin_reference(client, self.project_id, gender, angle_key)
        if angle_key == "135" and mannequin_mid:
            # Pose Guide MUST be first in character_media_ids so Google Flow prioritizes the 135° rotation and feet stance over symmetrical rear view
            char_refs = [mannequin_mid, ref_media_id]
            logger.info("Using Dual-Ref for %s angle %s° (Pose First): [mannequin=%s, identity=%s]", gender, angle_key, mannequin_mid[:8], ref_media_id[:8])
        else:
            char_refs = [ref_media_id]
            if mannequin_mid:
                char_refs.append(mannequin_mid)
            logger.info("Using Dual-Ref for %s angle %s°: [identity=%s, mannequin=%s]", gender, angle_key, ref_media_id[:8], mannequin_mid[:8] if mannequin_mid else "none")

        while not self._cancelled and retries < max_retries:
            retries += 1
            try:
                res = await client.generate_images(
                    prompt=prompt,
                    project_id=self.project_id,
                    aspect_ratio="IMAGE_ASPECT_RATIO_PORTRAIT",
                    user_paygate_tier=self.user_paygate_tier,
                    character_media_ids=char_refs,
                )
                if res.get("error"):
                    logger.warning("Stage 2 angle %s° API error: %s, retrying... (%d/%d)", angle_key, res.get("error"), retries, max_retries)
                    await asyncio.sleep(5)
                    continue
                media_id, url = self._extract_image_result(res)
                if not media_id:
                    logger.warning("Stage 2 angle %s° empty, retrying... (%d/%d)", angle_key, retries, max_retries)
                    await asyncio.sleep(5)
                    continue

                # Validate angle image & save locally for AI agent review
                if url:
                    val = await validate_and_save(image_url=url, angle=angle_key, attempt=retries)
                    self.angles[angle_key]["validation"] = val
                    self.angles[angle_key]["local_path"] = val.get("local_path")
                    if not val.get("downloaded") or not val.get("basic", {}).get("valid", True):
                        issues = val.get("basic", {}).get("issues", [])
                        logger.warning(
                            "Stage 2 angle %s° basic check failed (issues=%s), retrying... (%d/%d)",
                            angle_key, issues, retries, max_retries,
                        )
                        await asyncio.sleep(5)
                        continue
                    logger.info("Stage 2 angle %s° saved to %s (green_ratio=%s)", angle_key, val.get("local_path"), val.get("basic", {}).get("green_ratio"))

                self.angles[angle_key]["media_id"] = media_id
                self.angles[angle_key]["url"] = url
                self.angles[angle_key]["status"] = "COMPLETED"
                logger.info("Stage 2 angle %s° success: media_id=%s", angle_key, media_id[:8])
                return
            except Exception as e:
                logger.warning("Stage 2 angle %s° failed (%s), retrying... (%d/%d)", angle_key, e, retries, max_retries)
                await asyncio.sleep(5)

        logger.error("Stage 2 angle %s° exhausted %d retries", angle_key, max_retries)
        self.angles[angle_key]["status"] = "FAILED"

    async def _generate_4_angles(self) -> bool:
        """Stage 2: Generate 45°, 90°, 135°, 180° concurrently."""
        ref_id = self.angles["0"]["media_id"]
        if not ref_id:
            raise ValueError("Missing 0° reference image for Stage 2")

        tasks = [
            self._generate_single_angle(ang, ref_id)
            for ang in ["45", "90", "135", "180"]
        ]
        await asyncio.gather(*tasks)
        return all(self.angles[a]["status"] == "COMPLETED" for a in ["45", "90", "135", "180"])

    async def _run_sliding_window_actions(self):
        """Stage 3: Run 5 concurrent worker tasks consuming the queue continuously."""
        pending_queue = asyncio.Queue()
        for task in self.tasks:
            await pending_queue.put(task)

        workers = [
            asyncio.create_task(self._slot_worker(slot_idx, pending_queue))
            for slot_idx in range(5)
        ]
        await pending_queue.join()
        for w in workers:
            w.cancel()

    async def _slot_worker(self, slot_idx: int, queue: asyncio.Queue):
        """Worker bound to a specific slot index (0..4)."""
        while not self._cancelled:
            try:
                task = await queue.get()
            except asyncio.CancelledError:
                break

            slot_ref = self.slots[slot_idx]
            slot_ref["task_id"] = task["id"]
            slot_ref["name"] = task["name"]
            slot_ref["status"] = "RUNNING"
            start_t = time.time()

            success = False
            while not success and not self._cancelled:
                task["status"] = "RUNNING"
                success = await self._execute_video_task(task, slot_ref, start_t)
                if not success and not self._cancelled:
                    task["retries"] += 1
                    task["status"] = "RETRYING"
                    slot_ref["status"] = "RETRYING"
                    logger.warning("Task %s failed; retry #%d in 5s...", task["name"], task["retries"])
                    await asyncio.sleep(5)

            if success:
                task["status"] = "COMPLETED"
                logger.info("Task %s COMPLETED in slot %d", task["name"], slot_idx)

            slot_ref["task_id"] = None
            slot_ref["name"] = "Idle"
            slot_ref["status"] = "IDLE"
            slot_ref["elapsed_s"] = 0
            queue.task_done()

    async def _execute_video_task(self, task: dict, slot_ref: dict, start_t: float) -> bool:
        """Execute one 4s video loop with Start Frame = End Frame = Angle Image."""
        client = get_flow_client()
        ang = task["angle"]
        angle_info = self.angles.get(ang, {})
        media_id = angle_info.get("media_id")
        if not media_id:
            task["error"] = f"No media_id for angle {ang}"
            return False

        try:
            # Rule 5: Start Frame = End Frame = Image Media ID, 4s duration
            submit_res = await client.generate_video(
                start_image_media_id=media_id,
                end_image_media_id=media_id,
                duration=4.0,
                prompt=task["prompt"],
                project_id=self.project_id,
                scene_id=task["id"],
                aspect_ratio="VIDEO_ASPECT_RATIO_PORTRAIT",
                user_paygate_tier=self.user_paygate_tier,
            )
            operations = _extract_operations(submit_res, project_id=self.project_id)
            if not operations:
                err_detail = submit_res.get("error") or submit_res.get("data") or submit_res.get("status") or str(submit_res)[:120]
                logger.error("Video submit returned no operations: %s", str(submit_res)[:500])
                task["error"] = f"Submit error: {err_detail}"
                return False

            # Poll until finished
            poll_res = await _poll_operations(
                client, operations, timeout=300,
                scene_id=task["id"], orientation="PORTRAIT"
            )
            if poll_res.get("error"):
                task["error"] = poll_res["error"]
                return False

            # Extract video URL
            vid_mid = (
                operations[0].get("_primary_media_id")
                or operations[0].get("operation", {}).get("metadata", {}).get("video", {}).get("mediaId")
                or operations[0].get("name", "")
            )
            video_url = f"https://flow-content.google/video/{vid_mid}"
            task["output_url"] = video_url
            task["error"] = None
            slot_ref["elapsed_s"] = int(time.time() - start_t)
            return True
        except Exception as e:
            task["error"] = str(e)
            logger.warning("Video task execution exception: %s", e)
            return False

    def _extract_image_result(self, result: dict) -> tuple[Optional[str], Optional[str]]:
        """Extract mediaId and image URL from generate_images response."""
        data = result.get("data", result)
        if isinstance(data, dict):
            media_list = data.get("media", [])
            if media_list and isinstance(media_list, list):
                m = media_list[0]
                mid = m.get("name")
                img_block = m.get("image", {}) if isinstance(m.get("image"), dict) else {}
                gen_img = img_block.get("generatedImage", {}) if isinstance(img_block.get("generatedImage"), dict) else {}
                url = gen_img.get("fifeUrl") or img_block.get("fifeUrl") or m.get("fifeUrl")
                return mid, url
        return None, None


# ─── Pipeline Registry ────────────────────────────────────────

_PIPELINES: Dict[str, SkillTreePipeline] = {}


def create_pipeline(project_id: str, customizer_values: dict = None,
                    action_keys: list = None) -> SkillTreePipeline:
    pipeline = SkillTreePipeline(project_id, customizer_values, action_keys)
    _PIPELINES[pipeline.id] = pipeline
    return pipeline


def get_pipeline(pipeline_id: str) -> Optional[SkillTreePipeline]:
    return _PIPELINES.get(pipeline_id)


def list_pipelines() -> List[dict]:
    return [p.to_dict() for p in _PIPELINES.values()]

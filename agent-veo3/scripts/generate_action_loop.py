"""Universal Action Loop Generator for Characters.
Usage:
    python agent-veo3/scripts/generate_action_loop.py --character diep-thanh-lam --action idle --angle 0
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import struct
import sys
import uuid
import aiohttp

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent.services.prompt_templates import (
    format_template,
    get_action_templates,
    ANIMATION_PRIORITY_SEQUENCE,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("action_generator")

BASE_OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
PLANS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "plans"))

ACTION_FOLDER_MAP = {
    # Tier 1: Core Locomotion & Baseline
    "idle": ("dung-yen", "Đứng Yên"),
    "walk": ("di-bo", "Đi Bộ"),
    "run": ("chay", "Chạy"),
    # Tier 2: Acting, Etiquette & Social
    "wave": ("vay-tay", "Vẫy Tay Chào"),
    "bow": ("hanh-le", "Hành Lễ Cúi Chào"),
    "cover_mouth_laugh": ("che-mieng-cuoi", "Che Miệng Cười"),
    "cover-mouth": ("che-mieng-cuoi", "Che Miệng Cười"),
    "talking": ("noi-chuyen", "Nói Chuyện"),
    "nod": ("gat-dau", "Gật Đầu"),
    "think": ("suy-nghi", "Suy Nghĩ"),
    # Tier 3: Emotional Reactions
    "surprise": ("kinh-ngac", "Kinh Ngạc"),
    "cheer": ("reo-ho", "Reo Hò Ăn Mừng"),
    "sad": ("buon-ba", "Buồn Bã Thở Dài"),
    "angry": ("tuc-gian", "Tức Giận Dỗi"),
    # Tier 4: Combat & Impact
    "attack": ("danh-cong", "Đánh Công"),
    "defend": ("phong-thu", "Phòng Thủ"),
    "hurt": ("trung-don", "Trúng Đòn"),
}


LOOP_ACTIONS = {"walk", "run"}


def update_plan_file(character_key: str, action: str, angle: str, media_id: str, file_rel: str, size_bytes: int, duration: float = 4.0):
    """Update markdown plan file table with newly generated video."""
    plan_path = os.path.join(PLANS_DIR, f"{character_key}.plan_character_pipeline.md")
    if not os.path.exists(plan_path):
        return

    action_folder, action_label = ACTION_FOLDER_MAP.get(action.lower(), (action.lower(), action))
    size_kb = f"{size_bytes // 1024} KB" if size_bytes else "N/A"
    is_loop = action.lower() in LOOP_ACTIONS
    dur_str = f"**{duration:.2f}s**"
    type_str = "**Hoàn Thành** (Seamless Loop 4s i2v_fl)" if is_loop else "**Hoàn Thành** (Single Frame 8s i2v)"
    header_str = f"**{action_label} (Gốc {duration:.1f}s{' Loop' if is_loop else ''})**"
    new_line = f"| {header_str} | {angle}° | `{media_id}` | [{action}_{angle}.mp4](file:///e:/UngDung_PC/Flow-App/AI-Render-Video/agent-veo3/output/{character_key}/{file_rel}) | 720x1280, {dur_str}, {size_kb} | {type_str} |\n"

    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines(True)
        replaced = False
        for idx, line in enumerate(lines):
            if f"**{action_label}" in line and f"| {angle}° |" in line:
                lines[idx] = new_line
                replaced = True
                break

        if replaced:
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write("".join(lines))
            logger.info("Updated plan file (replaced row): %s", plan_path)
            return

        if "## 5. Registry Hoạt Ảnh Động Tác" in content:
            # Append to table
            parts = content.split("## 5. Registry Hoạt Ảnh Động Tác")
            table_part = parts[1]
            t_lines = table_part.splitlines(True)
            last_row_idx = -1
            for idx, line in enumerate(t_lines):
                if line.strip().startswith("|") and not line.strip().startswith("|---"):
                    last_row_idx = idx
            if last_row_idx >= 0:
                t_lines.insert(last_row_idx + 1, new_line)
                new_table_part = "".join(t_lines)
                content = parts[0] + "## 5. Registry Hoạt Ảnh Động Tác" + new_table_part
                with open(plan_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("Updated plan file: %s", plan_path)
    except Exception as e:
        logger.warning("Failed to update plan file: %s", e)


SUBMISSION_LOCK = asyncio.Lock()
META_LOCK = asyncio.Lock()


def get_mp4_duration(path: str) -> float:
    """Extract duration in seconds from MP4 mvhd atom without external tools."""
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        return 0.0
    try:
        with open(path, "rb") as f:
            data = f.read(8192)
        idx = data.find(b"mvhd")
        if idx != -1:
            v = data[idx + 4]
            if v == 0:
                ts, dur = struct.unpack(">II", data[idx + 16 : idx + 24])
            else:
                ts, dur = struct.unpack(">IQ", data[idx + 24 : idx + 36])
            return round(dur / ts, 2)
    except Exception:
        pass
    return 0.0


async def generate_action(character_key: str, action: str, angle: str, session: aiohttp.ClientSession = None, force: bool = False):
    char_dir = os.path.join(BASE_OUTPUT_DIR, character_key)
    meta_path = os.path.join(char_dir, "character_meta.json")

    if not os.path.exists(meta_path):
        logger.error("character_meta.json not found in %s", char_dir)
        return False

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    project_id = meta.get("project_id")
    angle_key = f"angle_{angle}"
    angle_data = meta.get(angle_key, {})
    media_id = angle_data.get("media_id")

    if not project_id or not media_id:
        logger.error("Missing project_id (%s) or media_id (%s) for %s", project_id, media_id, angle_key)
        return False

    action_folder, action_label = ACTION_FOLDER_MAP.get(action.lower(), (action.lower(), action))
    dest_dir = os.path.join(char_dir, action_folder)
    os.makedirs(dest_dir, exist_ok=True)

    # Check if already completed
    if not force:
        existing = meta.get("actions", {}).get(action_folder, {}).get(angle_key, {})
        if existing.get("status") == "COMPLETED" and os.path.exists(os.path.join(char_dir, existing.get("file", ""))):
            logger.info("Action '%s' %s° already completed for %s, skipping (use --force to overwrite).", action, angle, character_key)
            return True

    gender = meta.get("gender", "female")
    profile = meta.get("profile", {})
    is_male = (gender.lower() == "male")
    rear_belt_lock = (
        "Strictly continuous flat belt band behind back, ZERO bow, ZERO ribbon knot under natural gravity."
        if is_male
        else "Rear waist delicate silk ribbon sash draping calmly downward without flapping under natural gravity."
    )
    customizer = {
        "characterName": meta.get("name", "Character"),
        "gender": gender,
        "age": meta.get("age", profile.get("age", "young adult (20-22)")),
        "personality": profile.get("personality", "Thanh nhã thoát tục, tiêu sái phong khoáng"),
        "chromaBgHex": profile.get("chroma_bg", "#00FF00"),
        "skinTone": profile.get("skin", "Fair warm ivory natural skin tone"),
        "waistRearMotionLock": rear_belt_lock,
        "hairStyleColor": profile.get("hair", ""),
        "outfitDescription": profile.get("outfit", ""),
        "primaryColor": profile.get("primary_color", ""),
        "accentColor": profile.get("accent_color", ""),
        "weaponType": "None (empty hands, pure martial arts)",
        "spellElement": profile.get("combat_style", ""),
        "style": profile.get("style", "2D Xianxia/Fantasy manhwa anime chibi sprite"),
    }
    action_dict = get_action_templates(action.lower(), customizer)
    if not action_dict or angle not in action_dict:
        logger.error("No template found for action '%s' at angle '%s'", action, angle)
        return False

    raw_template = action_dict[angle]
    prompt = format_template(raw_template, customizer)

    is_loop = action.lower() in LOOP_ACTIONS
    duration_val = 4.0 if is_loop else 8.0

    logger.info("=" * 70)
    if is_loop:
        logger.info("[LOOP FRAME LOCK 4s] Action: '%s', Angle: %s° for %s", action, angle, character_key)
        logger.info(" -> START FRAME (mediaId): %s", media_id)
        logger.info(" -> END FRAME   (mediaId): %s", media_id)
    else:
        logger.info("[I2V CONTINUOUS 8s] Action: '%s', Angle: %s° for %s", action, angle, character_key)
        logger.info(" -> START FRAME (mediaId): %s", media_id)
        logger.info(" -> SINGLE FRAME IMAGE-TO-VIDEO (end_image=None)")
    logger.info(" -> PROMPT: %s...", prompt[:200])
    logger.info("=" * 70)

    url_gen = "http://127.0.0.1:8100/api/flow/generate-video"
    url_check = "http://127.0.0.1:8100/api/flow/check-status"

    body = {
        "start_image_media_id": media_id,
        "prompt": prompt,
        "project_id": project_id,
        "scene_id": f"scene_{action}_{angle}_{uuid.uuid4().hex[:6]}",
        "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "duration": duration_val,
        "duration_s": int(duration_val),
    }
    if is_loop:
        body["end_image_media_id"] = media_id

    own_session = False
    if session is None:
        session = aiohttp.ClientSession()
        own_session = True

    try:
        data = None
        async with SUBMISSION_LOCK:
            for submit_retry in range(10):
                try:
                    async with session.post(url_gen, json=body, timeout=60) as resp:
                        data = await resp.json()
                        if resp.status == 200 and not data.get("error"):
                            break
                        if "Extension not connected" in str(data) or "disconnected" in str(data).lower():
                            logger.warning("Extension reconnecting, waiting 5s (retry %d/10)...", submit_retry + 1)
                            await asyncio.sleep(5)
                            continue
                        logger.error("Submission failed: %s", data)
                        return False
                except (aiohttp.ClientError, asyncio.TimeoutError, Exception) as net_err:
                    logger.warning("Network/Server hiccup (%s), waiting 4s (retry %d/10)...", net_err, submit_retry + 1)
                    await asyncio.sleep(4)
                    continue
            else:
                logger.error("Submission failed after retries: %s", data)
                return False
            await asyncio.sleep(1.2)

        workflows = data.get("workflows", [])
        operations = data.get("operations", [])

        if not workflows and not operations:
            logger.error("No workflows or operations returned: %s", data)
            return False

        logger.info("Polling operation for %s %s°...", action, angle)
        vid_media_id = None
        signed_url = None

        if workflows:
            check_payload = {"workflows": workflows, "project_id": project_id}
            for poll in range(60):
                await asyncio.sleep(6)
                try:
                    async with session.post(url_check, json=check_payload, timeout=30) as c_resp:
                        sdata = await c_resp.json()
                except Exception as e:
                    logger.warning("Poll error: %s", e)
                    continue

                for wf in sdata.get("workflows", []):
                    st = wf.get("status", "")
                    if st in ("MEDIA_GENERATION_STATUS_SUCCESSFUL", "SUCCESSFUL") or wf.get("done"):
                        vid_media_id = wf.get("primary_media_id") or wf.get("media", {}).get("media_id")
                        signed_url = wf.get("media", {}).get("url")
                        break
                    if st in ("MEDIA_GENERATION_STATUS_FAILED", "FAILED"):
                        logger.error("Generation failed: %s", wf)
                        return False
                if vid_media_id:
                    break
        else:
            check_payload = {"operations": operations}
            for poll in range(60):
                await asyncio.sleep(6)
                try:
                    async with session.post(url_check, json=check_payload, timeout=30) as c_resp:
                        sdata = await c_resp.json()
                except Exception as e:
                    logger.warning("Poll error: %s", e)
                    continue

                for op in sdata.get("operations", []):
                    st = op.get("status", "")
                    if st in ("MEDIA_GENERATION_STATUS_SUCCESSFUL", "SUCCESSFUL"):
                        meta_vid = op.get("operation", {}).get("metadata", {}).get("video", {})
                        vid_media_id = meta_vid.get("mediaId")
                        signed_url = meta_vid.get("fifeUrl") or meta_vid.get("servingUri")
                        break
                    if st in ("MEDIA_GENERATION_STATUS_FAILED", "FAILED"):
                        logger.error("Generation failed: %s", op)
                        return False
                if vid_media_id:
                    break

        if not vid_media_id:
            logger.error("Polling timed out for %s %s°!", action, angle)
            return False

        logger.info("Generation SUCCESSFUL! Media ID: %s.", vid_media_id)
        if not signed_url:
            logger.info("Fetching signed CDN URL for %s...", vid_media_id)
            url_redirect = f"http://127.0.0.1:8100/api/flow/media-redirect-url/{vid_media_id}"
            for _ in range(10):
                try:
                    async with session.get(url_redirect, timeout=15) as r:
                        res_data = await r.json()
                        if res_data.get("status") == 200:
                            u = res_data.get("data", {}).get("url", "")
                            if u and "flow-content.google" in u:
                                signed_url = u
                                break
                except Exception as e:
                    logger.debug("Redirect poll error: %s", e)
                await asyncio.sleep(2)

        # Fallback to captured-video-urls
        if not signed_url:
            async with session.get("http://127.0.0.1:8100/api/flow/captured-video-urls") as r:
                urls = await r.json()
            for item in reversed(urls):
                u = item.get("url", "")
                if vid_media_id in u and ("/video/" in u or "flow-content.google" in u):
                    signed_url = u
                    break

        if not signed_url:
            logger.error("Signed video URL could not be obtained for %s!", vid_media_id)
            return False

        logger.info("Downloading MP4 for %s %s° from CDN...", action, angle)
        async with session.get(signed_url, timeout=90) as r:
            raw_bytes = await r.read()

        if len(raw_bytes) < 1000:
            logger.error("Downloaded file too small (%d bytes)!", len(raw_bytes))
            return False

        dest_vid = os.path.join(dest_dir, f"{action}_{angle}.mp4")
        with open(dest_vid, "wb") as f:
            f.write(raw_bytes)

        # Update metadata thread-safely
        async with META_LOCK:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            actions_dict = meta.setdefault("actions", {}).setdefault(action_folder, {})
            actions_dict[angle_key] = {
                "media_id": vid_media_id,
                "file": f"{action_folder}/{action}_{angle}.mp4",
                "duration": duration_val,
                "resolution": "720x1280",
                "size_bytes": os.path.getsize(dest_vid),
                "status": "COMPLETED",
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

        # Update markdown plan
        update_plan_file(character_key, action, angle, vid_media_id, f"{action_folder}/{action}_{angle}.mp4", os.path.getsize(dest_vid), duration=duration_val)

        logger.info("[SUCCESS] Generated %s %s° (Duration: %.1fs): %s (Size: %d bytes)", action, angle, duration_val, dest_vid, os.path.getsize(dest_vid))
        return True
    finally:
        if own_session:
            await session.close()



async def generate_action_with_retry(character_key: str, action: str, angle: str, session: aiohttp.ClientSession = None, force: bool = False, max_retries: int = 2) -> bool:
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.warning("[RETRY %d/%d] Retrying %s %s° for %s...", attempt, max_retries, action, angle, character_key)
            await asyncio.sleep(4)
        try:
            success = await generate_action(character_key, action, angle, session=session, force=force)
            if success:
                return True
        except Exception as e:
            logger.warning("Error during %s %s° (attempt %d): %s", action, angle, attempt + 1, e)
    return False


async def run_batch(character_key: str, tasks: list[tuple[str, str]], concurrency: int = 5, force: bool = False):
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        async def _worker(act, ang, idx: int):
            # Stagger startup slightly so parallel requests do not clash on websocket
            await asyncio.sleep(min(idx * 0.8, 4.0))
            async with sem:
                logger.info("=== Starting [%s %s°] ===", act, ang)
                success = await generate_action_with_retry(character_key, act, ang, session=session, force=force)
                logger.info("=== Finished [%s %s°]: %s ===", act, ang, "OK" if success else "FAILED")
                return success

        results = await asyncio.gather(*[_worker(act, ang, i) for i, (act, ang) in enumerate(tasks)])
        logger.info("Batch summary: %d/%d successful", sum(results), len(results))


def inspect_character_pipeline(character_key: str, actions: list[str] = None) -> tuple[dict, list[tuple[str, str]]]:
    """Inspect character_meta.json and return (report_dict, pending_tasks_in_priority_order)."""
    char_dir = os.path.join(BASE_OUTPUT_DIR, character_key)
    meta_path = os.path.join(char_dir, "character_meta.json")
    if not os.path.exists(meta_path):
        logger.error("character_meta.json not found in %s", char_dir)
        return {}, []

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    angles = ["0", "45", "90", "135", "180"]
    action_list = actions or ANIMATION_PRIORITY_SEQUENCE

    base_ready = {}
    for ang in angles:
        adata = meta.get(f"angle_{ang}", {})
        has_id = bool(adata.get("media_id"))
        is_completed = adata.get("status") in ("COMPLETED", "SUCCESSFUL") or has_id
        file_path = os.path.join(char_dir, adata.get("file", f"angle_{ang}.png"))
        file_ok = os.path.exists(file_path) and os.path.getsize(file_path) > 1000
        base_ready[ang] = {
            "ready": bool(has_id and is_completed),
            "has_local_file": file_ok,
            "media_id": adata.get("media_id"),
        }

    missing_tasks = []
    matrix = {}

    for act in action_list:
        folder, label = ACTION_FOLDER_MAP.get(act, (act, act))
        act_entry = meta.get("actions", {}).get(folder, {})
        matrix[act] = {"label": label, "folder": folder, "angles": {}}

        for ang in angles:
            ang_data = act_entry.get(f"angle_{ang}", {})
            vid_id = ang_data.get("media_id")
            vid_file = ang_data.get("file", f"{folder}/{act}_{ang}.mp4")
            vid_path = os.path.join(char_dir, vid_file)
            has_local = os.path.exists(vid_path) and os.path.getsize(vid_path) > 1000
            is_loop = act.lower() in LOOP_ACTIONS
            expected_dur = 4.0 if is_loop else 8.0
            cur_dur = ang_data.get("duration", 0.0)
            if (cur_dur == 0.0 or abs(cur_dur - expected_dur) > 0.5) and has_local:
                cur_dur = get_mp4_duration(vid_path)
            dur_ok = abs(cur_dur - expected_dur) <= 0.5
            is_ok = has_local and dur_ok

            matrix[act]["angles"][ang] = {
                "ok": is_ok,
                "has_local": has_local,
                "file": vid_file if has_local else None,
                "media_id": vid_id,
            }

            if not is_ok:
                missing_tasks.append((act, ang))

    return {
        "character_key": character_key,
        "project_id": meta.get("project_id"),
        "base_angles": base_ready,
        "matrix": matrix,
    }, missing_tasks


def print_status_report(report: dict, pending_tasks: list[tuple[str, str]]):
    angles = ["0", "45", "90", "135", "180"]
    print("\n" + "=" * 80)
    print(f"TIẾN ĐỘ HOẠT HÌNH: Nhân Vật [{report['character_key']}]")
    print(f"Project ID Google Flow: {report.get('project_id')}")
    print("-" * 80)
    base_str = "  ".join([f"{a}°: {'[OK]' if report['base_angles'].get(a, {}).get('ready') else '[THIẾU]'}" for a in angles])
    print(f"5 Ảnh Mốc Cơ Bản: {base_str}")
    print("-" * 80)
    print(f"{'Hành Động (Action)':<22} | {'0°':<5} | {'45°':<5} | {'90°':<5} | {'135°':<5} | {'180°':<5} | Tiến Độ")
    print("-" * 80)

    for act, data in report["matrix"].items():
        label = data["label"]
        statuses = []
        done_count = 0
        for ang in angles:
            ok = data["angles"][ang]["ok"]
            if ok:
                done_count += 1
                statuses.append(" OK  ")
            else:
                statuses.append(" --- ")
        prog = f"{done_count}/5 ({done_count * 20}%)"
        print(f"{label:<22} | " + " | ".join(statuses) + f" | {prog}")

    print("=" * 80)
    print(f"-> Tổng animation còn thiếu: {len(pending_tasks)} video 4s loop")
    if pending_tasks:
        print("-> Trình tự ưu tiên cần tạo tiếp:")
        for idx, (act, ang) in enumerate(pending_tasks[:8], 1):
            folder, label = ACTION_FOLDER_MAP.get(act, (act, act))
            print(f"   [{idx}] {label} ({act}) góc {ang}°")
        if len(pending_tasks) > 8:
            print(f"   ... và {len(pending_tasks) - 8} task tiếp theo.")
    else:
        print("-> CHÚC MỪNG: Tất cả hoạt ảnh animation trong pipeline đều đã HOÀN THÀNH 100%!")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate seamless action loops for characters.")
    parser.add_argument("--character", required=True, help="Character key (e.g. diep-thanh-lam)")
    parser.add_argument("--action", default=None, help="Action name: idle, walk, run, wave, bow, etc.")
    parser.add_argument("--angle", default=None, help="Angle: 0, 45, 90, 135, 180 (or comma-separated)")
    parser.add_argument("--status", action="store_true", help="Inspect character_meta.json and show progress report")
    parser.add_argument("--resume", action="store_true", help="Auto-read character_meta.json & plan, generate missing in priority order")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of missing animation tasks to run (0 = all)")
    parser.add_argument("--all", action="store_true", help="Generate all actions for all angles")
    parser.add_argument("--force", action="store_true", help="Force re-generation and overwrite existing videos")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent generations (default: 5)")
    args = parser.parse_args()

    all_angles = ["0", "45", "90", "135", "180"]

    if args.status:
        report, pending = inspect_character_pipeline(args.character)
        print_status_report(report, pending)
        return

    if args.resume:
        report, pending = inspect_character_pipeline(args.character)
        print_status_report(report, pending)
        if not pending:
            logger.info("Nothing to resume! All animations completed for %s.", args.character)
            return

        tasks = pending
        if args.limit > 0:
            tasks = tasks[:args.limit]
            logger.info("Applying --limit %d: Running %d missing tasks in priority order.", args.limit, len(tasks))
        else:
            logger.info("Resuming %d missing tasks in strict priority order for %s...", len(tasks), args.character)

        asyncio.run(run_batch(args.character, tasks, concurrency=args.concurrency, force=args.force))
        return

    if args.all:
        tasks = [(act, ang) for act in ANIMATION_PRIORITY_SEQUENCE for ang in all_angles]
        logger.info("Queued ALL %d action-angle combinations for %s (concurrency: %d, force: %s)", len(tasks), args.character, args.concurrency, args.force)
        asyncio.run(run_batch(args.character, tasks, concurrency=args.concurrency, force=args.force))
    elif args.action:
        acts = [a.strip() for a in args.action.split(",")]
        angs = [a.strip() for a in args.angle.split(",")] if args.angle else all_angles
        tasks = [(act, ang) for act in acts for ang in angs]
        if len(tasks) == 1:
            act, ang = tasks[0]
            asyncio.run(generate_action(args.character, act, ang, force=args.force))
        else:
            logger.info("Queued %d tasks (actions=%s, angles=%s, concurrency: %d, force: %s)", len(tasks), acts, angs, args.concurrency, args.force)
            asyncio.run(run_batch(args.character, tasks, concurrency=args.concurrency, force=args.force))
    else:
        # Default: show status and guide
        report, pending = inspect_character_pipeline(args.character)
        print_status_report(report, pending)
        print("Gợi ý: Dùng --resume để tự động tạo tiếp các animation còn thiếu theo đúng thứ tự ưu tiên!")


if __name__ == "__main__":
    main()



"""Pipeline Tự Động Hoá Chuỗi Nâng Cấp Kế Thừa (Chained Image Upgrade) & Sinh Video Song Song.
Quy trình:
1. Pha 1: Chuỗi kế thừa hình ảnh: Ảnh 1 -> Ảnh 2 -> ... -> Ảnh 10 (mỗi ảnh lấy ảnh trước đó làm ref).
2. Pha 2: Sinh Video Song Song (Parallel Generation): Gửi đồng thời các cảnh, polling tập trung và tải về ngay khi xong.
3. Pha 3: Ghép nối 10 clips 8s thành Master Video 80s bằng OpenCV.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
import urllib.request
import aiohttp
import cv2

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_DIR = SCRIPT_DIR.parent
BASE_OUT = AGENT_DIR / "output" / "upgrade_10_scenes"
API_BASE = "http://127.0.0.1:8100"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("chained_upgrade_pipeline")

PROJECT_ID = "f762d7dd-63d3-4a43-a5bc-6c3fb2072839"
BUILDER_REF = "64e7534b-0a9d-4c75-ba56-30909692ea6a"

SCENES_DEF = [
    {
        "index": 1,
        "title": "01_Khao_Sat_Va_Dat_Mong",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic daylight. "
            "Isometric 3D diorama angle of an open grassy clearing on a floating diorama ground tile. "
            "Tiny_Builder is driving wooden stakes into the soft soil. A small wooden wheelbarrow filled with foundation stones sits nearby. "
            "NO text, NO letters, NO numbers, clean game asset render, bright cheerful lighting."
        ),
        "video_prompt": (
            "0-3s: Tiny_Builder taps wooden survey pegs into the green meadow, kicking up gentle cartoon grass puffs. "
            "3-6s: A wooden wheelbarrow tips forward, dumping rough grey foundation stones into a dug trench; the stones slide neatly into a square boundary. "
            "6-8s: The square foundation outline settles firmly into the turf as dust clears and the builder inspects his work. NO text, NO numbers."
        ),
    },
    {
        "index": 2,
        "title": "02_Dung_Khung_Go_Moc",
        "image_prompt": (
            "Taking the exact same diorama floating tile, ground, and stone foundation from the reference image, "
            "construct 4 heavy solid wooden timber corner posts and interlocking crossbeams erecting the structural frame onto the stone foundation. "
            "Horizontal wooden beams connect the posts with traditional mortise carpentry. Tiny_Builder holds an axe. "
            "NO text, NO letters, clean stylized 3D diorama."
        ),
        "video_prompt": (
            "0-3s: Cylindrical tree logs roll into the work site; Tiny_Builder notches the beam ends with his tool. "
            "3-6s: Four sturdy corner posts lift upright and plant into the stone bases; horizontal crossbeams fly in and snap firmly into place with yellow cartoon spark particles. "
            "6-8s: The solid wooden post-and-beam timber frame stands firm, ready for walls. NO text, NO numbers."
        ),
    },
    {
        "index": 3,
        "title": "03_Tram_Go_Cap_1",
        "image_prompt": (
            "Keeping the exact same diorama perspective and wooden frame from the reference image, "
            "enclose the walls with horizontal wooden planks and add an earthy canvas canopy roof to complete the level 1 wooden cabin outpost. "
            "Stacked wooden supply barrels and crates sit neatly in the yard. Thin wisps of smoke rise from a chimney. "
            "NO text, NO letters, stylized 3D game outpost."
        ),
        "video_prompt": (
            "0-3s: Wooden wall planks slide into position, sealing the outer walls as Tiny_Builder hammers wooden pegs. "
            "3-6s: An earthy brown canvas roof canopy unfurls tightly across the rafters; wooden supply barrels roll into an orderly stack outside. "
            "6-8s: The cozy wooden cabin outpost settles with a happy vibration; a gentle smoke trail rises from the roof chimney. NO text, NO numbers."
        ),
    },
    {
        "index": 4,
        "title": "04_Op_Tuong_Da_Hoa_Cuong",
        "image_prompt": (
            "Keeping the exact same diorama wooden cabin from the reference image, "
            "reinforce the lower perimeter walls with layers of fitted white cobblestone blocks into a fortress stone foundation. "
            "The lower half of the walls transforms from timber to impenetrable smooth stone masonry. "
            "NO text, NO words, clean mobile strategy game render."
        ),
        "video_prompt": (
            "0-3s: Wheelbarrows loaded with polished white cobblestone blocks pull up to the building base as mortar is spread. "
            "3-6s: Rows of neatly cut stone blocks fly upward and wrap around the lower wooden perimeter, interlocking like tight masonry. "
            "6-8s: The reinforced stone battlement foundation locks solidly in place, giving the outpost a formidable fortress look. NO text, NO numbers."
        ),
    },
    {
        "index": 5,
        "title": "05_Lop_Ngoi_Xanh_Coban",
        "image_prompt": (
            "Keeping the exact same stone-reinforced structure from the reference image, "
            "extend a second stone floor with steep pitched roof covered in glossy cobalt-blue tiles. "
            "Arched stone windows and a fluttering royal blue pennant banner adorn the second tier. "
            "NO text, NO letters, vibrant Pixar lighting."
        ),
        "video_prompt": (
            "0-3s: A second stone floor extends upward from the main structure, adding arched windows and an observation balcony. "
            "3-6s: Hundreds of glossy cobalt-blue roof tiles cascade down in synchronized harmony, locking across the steep gables. "
            "6-8s: A deep blue triangular pennant flag unfurls from the pinnacle; warm golden lantern light shines through the windows. NO text, NO numbers."
        ),
    },
    {
        "index": 6,
        "title": "06_Guong_Nuoc_Va_Co_Khi",
        "image_prompt": (
            "Keeping the exact same building and diorama angle from the reference image, "
            "add a stone water canal on the side with a large rotating wooden waterwheel and interlocking cogs. "
            "An automated rope pulley mechanism lifts supply baskets. "
            "NO text, NO letters, charming mechanics."
        ),
        "video_prompt": (
            "0-3s: Crystal clear water gushes through an adjoining stone aqueduct canal, turning a massive handcrafted wooden waterwheel. "
            "3-6s: The spinning waterwheel engages internal wooden gear cogs that clack rhythmically, driving an automated rope pulley hoist. "
            "6-8s: Baskets of building materials glide swiftly up to the top floor on the pulley; water droplets sparkle in the sun. NO text, NO numbers."
        ),
    },
    {
        "index": 7,
        "title": "07_Xuong_Ren_Va_Lo_Luyen",
        "image_prompt": (
            "Keeping the exact same building and diorama from the reference image, "
            "attach a stone blacksmith forge with glowing coals, an anvil, and a brick chimney puffing cartoon smoke rings. "
            "Polished metal shields and iron reinforcement straps hang on the stone entrance. "
            "NO text, NO letters, warm fire glow."
        ),
        "video_prompt": (
            "0-3s: Glowing red-hot iron ingots are poured into the stone forge crucible as a mechanized hammer strikes the anvil with bright sparks. "
            "3-6s: The brick forge chimney rises, rhythmically puffing out playful round cartoon smoke rings into the clear blue sky. "
            "6-8s: Polished steel shields and iron reinforcement straps automatically bolt onto the fortress entrance, radiating durability. NO text, NO numbers."
        ),
    },
    {
        "index": 8,
        "title": "08_Nap_Pha_Le_Ma_Thuat",
        "image_prompt": (
            "Keeping the exact same building and diorama from the reference image, "
            "mount a radiant glowing cyan arcane energy crystal atop a carved stone pedestal on the central spire. "
            "Luminous blue circuit grooves trace through the stone walls, with floating crystal shards orbiting the peak. "
            "NO text, NO letters, magical 3D diorama."
        ),
        "video_prompt": (
            "0-3s: A radiant glowing cyan energy crystal is hoisted into a carved stone pedestal on the central fortress spire. "
            "3-6s: The crystal pulses with a brilliant cyan shockwave; intricate carved rune grooves throughout the fortress walls illuminate with bright blue light. "
            "6-8s: Small weightless stone pebbles float gently around the spire in a shimmering protective aura. NO text, NO numbers."
        ),
    },
    {
        "index": 9,
        "title": "09_Dai_Nang_Cap_Phao_Dai_Doi",
        "image_prompt": (
            "Keeping the exact same central fortress from the reference image, "
            "expand the base outward with twin flanking stone watchtowers connected by arched skybridges and a heavy iron portcullis gate. "
            "Burning torches illuminate the battlements. "
            "NO text, NO letters, epic castle render."
        ),
        "video_prompt": (
            "0-3s: Twin flanking stone watchtowers rise symmetrically on both sides of the main keep, joined by a grand arched stone skybridge. "
            "3-6s: Heavy iron portcullis gates with thick bronze chains slide down to lock the main archway with a heavy, satisfying thud. "
            "6-8s: Torches along the battlements ignite simultaneously with warm flames; the entire citadel stands fully enclosed and fortified. NO text, NO numbers."
        ),
    },
    {
        "index": 10,
        "title": "10_Dai_Canh_De_Che_Hoan_Thien",
        "image_prompt": (
            "The ultimate completed fantasy royal citadel with glowing crystal spire, spinning waterwheel, smoking forge, "
            "cobalt roofs, golden weather vanes, waving banners, set on a lush floating grassy island under golden sunlight. "
            "NO text, NO letters, masterpiece 8k 3D animation."
        ),
        "video_prompt": (
            "0-3s: The camera embarks on a majestic, smooth 360-degree orbital pan around the sprawling, completed fantasy royal citadel. "
            "3-6s: All systems operate harmoniously—waterwheel churning, arcane crystal glowing, golden banners fluttering, chimney smoke curling gently. "
            "6-8s: Colorful celebratory cartoon confetti drifts through the sunny sky as camera pulls back to display the full flourishing diorama. NO text, NO numbers."
        ),
    },
]


def setup_dirs() -> Dict[str, Path]:
    imgs_dir = BASE_OUT / "images"
    clips_dir = BASE_OUT / "clips"
    for d in (BASE_OUT, imgs_dir, clips_dir):
        d.mkdir(parents=True, exist_ok=True)
    return {
        "base": BASE_OUT,
        "images": imgs_dir,
        "clips": clips_dir,
        "manifest": BASE_OUT / "manifest.json",
    }


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"scenes": {}}


def save_manifest(manifest_path: Path, data: Dict[str, Any]):
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── PHA 1: CHUỖI NÂNG CẤP ẢNH KẾ THỪA (1 -> 10) ──────────────────────────

async def generate_chained_image(
    session: aiohttp.ClientSession,
    scene_spec: Dict[str, Any],
    prev_image_media_id: Optional[str],
    dirs: Dict[str, Path],
    manifest: Dict[str, Any],
) -> str:
    idx = scene_spec["index"]
    scene_key = f"scene_{idx:02d}"
    saved_meta = manifest["scenes"].get(scene_key, {})

    # Tối đa 2-3 ảnh tham chiếu: Ảnh trước đó + Thợ xây
    refs = [BUILDER_REF]
    if prev_image_media_id:
        refs.insert(0, prev_image_media_id)  # Ưu tiên ảnh trước làm ref chính

    logger.info("[PHA 1 KẾ THỪA] Sinh Ảnh #%02d [%s] (Dùng ref: %s)...", idx, scene_spec["title"], refs[:2])
    url = f"{API_BASE}/api/flow/generate-image"
    payload = {
        "prompt": scene_spec["image_prompt"],
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "character_media_ids": refs,
    }

    try:
        async with session.post(url, json=payload, timeout=120) as resp:
            data = await resp.json()
            media_list = data.get("media", [])
            if not media_list and isinstance(data.get("data"), dict):
                media_list = data["data"].get("media", [])

            if not media_list:
                logger.error("[LỖI PHA 1] Cảnh #%02d không có media trả về: %s", idx, data)
                return ""

            media_item = media_list[0]
            mid = media_item.get("name") or media_item.get("id")
            img_block = media_item.get("image", {}) if isinstance(media_item.get("image"), dict) else {}
            gen_img = img_block.get("generatedImage", {}) if isinstance(img_block.get("generatedImage"), dict) else {}
            fife_url = gen_img.get("fifeUrl") or img_block.get("fifeUrl") or media_item.get("fifeUrl")

            # Tải ảnh về lưu trữ
            img_path = dirs["images"] / f"{scene_key}.jpg"
            if fife_url:
                urllib.request.urlretrieve(fife_url, str(img_path))

            saved_meta["image_media_id"] = mid
            saved_meta["image_url"] = fife_url
            saved_meta["title"] = scene_spec["title"]
            manifest["scenes"][scene_key] = saved_meta
            save_manifest(dirs["manifest"], manifest)
            logger.info("✅ [PHA 1 XONG] Cảnh #%02d -> media_id: %s", idx, mid)
            return mid
    except Exception as exc:
        logger.exception("[LỖI PHA 1] Cảnh #%02d gặp ngoại lệ: %s", idx, exc)
        return ""


# ─── PHA 2: SINH VIDEO ĐỒNG THỜI SONG SONG (PARALLEL GENERATION) ───────────

async def submit_video_request(
    session: aiohttp.ClientSession,
    scene_spec: Dict[str, Any],
    image_media_id: str,
    dirs: Dict[str, Path],
    manifest: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    idx = scene_spec["index"]
    scene_key = f"scene_{idx:02d}"
    saved_meta = manifest["scenes"].get(scene_key, {})

    logger.info("[PHA 2 SUBMIT] Gửi yêu cầu sinh video Cảnh #%02d...", idx)
    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": image_media_id,
        "prompt": scene_spec["video_prompt"],
        "project_id": PROJECT_ID,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "duration": 8.0,
        "title": f"Scene_{idx:02d}_{scene_spec['title']}",
    }

    try:
        async with session.post(url, json=payload, timeout=120) as resp:
            data = await resp.json()
            ops = data.get("operations", [])
            if not ops and isinstance(data.get("data"), dict):
                ops = data["data"].get("operations", [])
            if ops:
                op_name = ops[0].get("operation", {}).get("name") or ops[0].get("name")
                logger.info("🚀 [SUBMITTED] Cảnh #%02d thành công -> Operation: %s", idx, op_name)
                saved_meta["operation"] = op_name
                manifest["scenes"][scene_key] = saved_meta
                save_manifest(dirs["manifest"], manifest)
                return {"idx": idx, "scene_key": scene_key, "operation": op_name}
            else:
                logger.error("[LỖI SUBMIT] Cảnh #%02d không có operations: %s", idx, data)
    except Exception as exc:
        logger.exception("[EXCEPTION SUBMIT] Cảnh #%02d: %s", idx, exc)
    return None


async def parallel_poll_all_videos(
    session: aiohttp.ClientSession,
    submitted_ops: List[Dict[str, Any]],
    dirs: Dict[str, Path],
    manifest: Dict[str, Any],
):
    """Polling đồng thời tất cả các operations của 10 video."""
    url = f"{API_BASE}/api/flow/check-status"
    pending = list(submitted_ops)
    start_t = time.time()
    logger.info("=== BẮT ĐẦU POLLING TẬP TRUNG CHO %d VIDEO CLIPS ===", len(pending))

    while pending:
        elapsed = int(time.time() - start_t)
        payload = {
            "operations": [
                {"operation": {"name": c["operation"]}, "status": "MEDIA_GENERATION_STATUS_PENDING"}
                for c in pending
            ]
        }

        try:
            async with session.post(url, json=payload, timeout=60) as resp:
                data = await resp.json()
                ops_list = data.get("operations", [])
                still_pending = []

                for cand in pending:
                    op_name = cand["operation"]
                    idx = cand["idx"]
                    scene_key = cand["scene_key"]
                    matched_url = None

                    for op_item in ops_list:
                        item_op = op_item.get("operation", {})
                        name = item_op.get("name") or op_item.get("name")
                        status = op_item.get("status")
                        if name == op_name and status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                            meta_video = item_op.get("metadata", {}).get("video", {})
                            matched_url = meta_video.get("fifeUrl") or meta_video.get("url")
                            break

                    if matched_url:
                        clip_path = dirs["clips"] / f"{scene_key}.mp4"
                        logger.info("🎉 [RENDER XONG] Cảnh #%02d hoàn thành sau %ds! Đang tải về...", idx, elapsed)
                        try:
                            urllib.request.urlretrieve(matched_url, str(clip_path))
                            manifest["scenes"][scene_key]["video_url"] = matched_url
                            manifest["scenes"][scene_key]["video_completed"] = True
                            manifest["scenes"][scene_key]["video_file"] = str(clip_path)
                            save_manifest(dirs["manifest"], manifest)
                            logger.info("💾 Đã lưu: %s (%0.2f MB)", clip_path.name, os.path.getsize(clip_path) / (1024 * 1024))
                        except Exception as dl_err:
                            logger.error("Lỗi khi tải Cảnh #%02d: %s", idx, dl_err)
                    else:
                        still_pending.append(cand)

                pending = still_pending
        except Exception as exc:
            logger.warning("Lỗi khi polling tập trung: %s", exc)

        if pending:
            logger.info("⏳ [%ds] Đang chờ %d/%d video clips hoàn thành...", elapsed, len(pending), len(submitted_ops))
            await asyncio.sleep(12)


# ─── PHA 3: GHÉP NỐI MASTER 80S (OPENCV) ───────────────────────────────────

def stitch_master_video(dirs: Dict[str, Path]) -> Optional[Path]:
    logger.info("=== PHA 3: GHÉP NỐI 10 CLIPS THÀNH MASTER VIDEO 80S ===")
    master_path = dirs["base"] / "master_upgrade_80s.mp4"
    clip_files = [dirs["clips"] / f"scene_{i:02d}.mp4" for i in range(1, 11)]

    valid_clips = [p for p in clip_files if p.exists() and p.stat().st_size > 0]
    if not valid_clips:
        logger.error("Không có clip nào để ghép nối!")
        return None

    logger.info("Tìm thấy %d/%d clips sẵn sàng để ghép nối.", len(valid_clips), len(clip_files))

    first_cap = cv2.VideoCapture(str(valid_clips[0]))
    width = int(first_cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(first_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps = first_cap.get(cv2.CAP_PROP_FPS) or 24.0
    first_cap.release()

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(master_path), fourcc, fps, (width, height))

    total_frames = 0
    for clip_p in valid_clips:
        logger.info("Đang ghép: %s", clip_p.name)
        cap = cv2.VideoCapture(str(clip_p))
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if (frame.shape[1], frame.shape[0]) != (width, height):
                frame = cv2.resize(frame, (width, height))
            writer.write(frame)
            total_frames += 1
        cap.release()

    writer.release()
    total_sec = total_frames / fps
    logger.info("🎉 GHÉP NỐI THÀNH CÔNG! Master: %s (%0.1f giây, %d frames)", master_path, total_sec, total_frames)
    return master_path


# ─── MAIN ORCHESTRATOR ─────────────────────────────────────────────────────

async def main():
    dirs = setup_dirs()
    manifest = {"scenes": {}}  # Tạo mới hoàn toàn theo yêu cầu người dùng
    save_manifest(dirs["manifest"], manifest)
    logger.info("=== BẮT ĐẦU PIPELINE CHUỖI KẾ THỪA & SINH SONG SONG (10 CẢNH 80S) ===")

    async with aiohttp.ClientSession() as session:
        # PHA 1: Chuỗi kế thừa hình ảnh (1 -> 10)
        logger.info(">>> BẮT ĐẦU PHA 1: CHUỖI NÂNG CẤP HÌNH ẢNH KẾ THỪA (1 -> 10) <<<")
        current_ref_id = None
        images_map = {}

        for sc in SCENES_DEF:
            img_id = await generate_chained_image(session, sc, current_ref_id, dirs, manifest)
            if img_id:
                current_ref_id = img_id  # Ảnh này trở thành ảnh tham chiếu cho cảnh tiếp theo!
                images_map[sc["index"]] = img_id
            await asyncio.sleep(2)

        # PHA 2: Sinh Video Đồng Thời Song Song (Parallel Generation)
        logger.info(">>> BẮT ĐẦU PHA 2: SINH ĐỒNG THỜI SONG SONG 10 VIDEO CLIPS 8S <<<")
        # Gửi theo batch 3-4 video cùng lúc để không nghẽn mạng
        sem = asyncio.Semaphore(4)
        submitted_ops = []

        async def bounded_submit(sc):
            async with sem:
                img_id = images_map.get(sc["index"])
                if img_id:
                    res = await submit_video_request(session, sc, img_id, dirs, manifest)
                    if res:
                        submitted_ops.append(res)
                await asyncio.sleep(1)

        await asyncio.gather(*[bounded_submit(sc) for sc in SCENES_DEF])

        # Polling tập trung đồng thời tất cả các video
        if submitted_ops:
            await parallel_poll_all_videos(session, submitted_ops, dirs, manifest)

    # PHA 3: Ghép nối Master Video 80s
    stitch_master_video(dirs)
    logger.info("=== HOÀN TẤT TRỌN VẸN TOÀN BỘ 10 PHÂN CẢNH 80S ===")


if __name__ == "__main__":
    asyncio.run(main())

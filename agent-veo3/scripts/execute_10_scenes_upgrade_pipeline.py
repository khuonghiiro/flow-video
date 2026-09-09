"""Pipeline Tự Động Hoá 10 Phân Cảnh (80 Giây) Nâng Cấp Công Trình Phong Cách Game.
Thực hiện 3 pha khép kín:
- Pha 1: Sinh trước toàn bộ 10 ảnh bối cảnh (Image-First Consistency) dùng ảnh tham chiếu.
- Pha 2: Dùng Image-to-Video sinh 10 video clips 8s (Sub-clip Timing 0-3s, 3-6s, 6-8s - KHÔNG CHỮ).
- Pha 3: Ghép nối (Stitch) 10 video clips thành master_upgrade_80s.mp4 bằng OpenCV.
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
logger = logging.getLogger("upgrade_10_pipeline")

PROJECT_ID = "f762d7dd-63d3-4a43-a5bc-6c3fb2072839"
BUILDER_REF = "64e7534b-0a9d-4c75-ba56-30909692ea6a"
OUTPOST_REF = "8545129b-f20e-466e-b4ce-98ffd64631bf"

SCENES_DEF = [
    {
        "index": 1,
        "title": "Khao_Sat_Va_Dat_Mong",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic daylight. "
            "Isometric 3D diorama angle of an open grassy clearing on a floating diorama tile. "
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
        "title": "Dung_Khung_Go_Moc",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Isometric 3D diorama angle of the stone foundation with heavy timber logs and posts erected at the four corners. "
            "Horizontal wooden crossbeams connect the pillars with traditional mortise joints. Tiny_Builder holds an axe. "
            "NO text, NO letters, NO words, clean stylized game diorama."
        ),
        "video_prompt": (
            "0-3s: Cylindrical tree logs roll into the work site; Tiny_Builder notches the beam ends with his tool. "
            "3-6s: Four sturdy corner posts lift upright and plant into the stone bases; horizontal crossbeams fly in and snap firmly into place with yellow cartoon spark particles. "
            "6-8s: The solid wooden post-and-beam timber frame stands firm, ready for walls. NO text, NO numbers."
        ),
    },
    {
        "index": 3,
        "title": "Tram_Go_Cap_1",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Isometric 3D diorama angle of a completed cozy Level 1 wooden outpost with horizontal plank walls, canvas canopy roof, "
            "and stacked supply crates and barrels in the yard. Thin wisps of smoke rise from a chimney. "
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
        "title": "Op_Tuong_Da_Hoa_Cuong",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Isometric 3D diorama view of the outpost undergoing masonry reinforcement. Smooth white cobblestones are being layered "
            "around the wooden lower walls, transforming the base into an impenetrable stone fortification. "
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
        "title": "Lop_Ngoi_Xanh_Coban",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Isometric 3D diorama view of the upgraded two-story fortress featuring a steep pitched roof covered in glossy cobalt-blue tiles. "
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
        "title": "Guong_Nuoc_Va_Co_Khi",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Isometric 3D diorama view of the fortress with a stone water canal along the side, powering a large churning wooden waterwheel. "
            "Interlocking wooden cogs and a rope hoist mechanism lift supply baskets. "
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
        "title": "Xuong_Ren_Va_Lo_Luyen",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Isometric 3D diorama view of an attached stone blacksmith forge with glowing orange coals, an anvil, and a brick chimney puffing cartoon smoke rings. "
            "Polished metal shields hang on the outer stone wall. "
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
        "title": "Nap_Pha_Le_Ma_Thuat",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Isometric 3D diorama view of the fortress with an arcane glowing cyan crystal mounted atop a pedestal on the central spire. "
            "Luminous blue energy channels trace through geometric grooves in the stone floors and walls. "
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
        "title": "Dai_Nang_Cap_Phao_Dai_Doi",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Isometric 3D diorama view of an expansive grand double-tower fortress with arched stone skybridges connecting the battlements. "
            "A heavy iron-studded portcullis gate with brass chains guards the reinforced front entrance. "
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
        "title": "Dai_Canh_De_Che_Hoan_Thien",
        "image_prompt": (
            "3D animated Pixar-quality rendering, vibrant colors, cinematic lighting. "
            "Wide isometric 3D diorama shot of the ultimate completed Royal Citadel. Glowing cyan crystal spire, spinning waterwheel, "
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


# ─── PHA 1: SINH TOÀN BỘ 10 ẢNH SCENE ──────────────────────────────────────

async def generate_scene_image(
    session: aiohttp.ClientSession,
    scene_spec: Dict[str, Any],
    dirs: Dict[str, Path],
    manifest: Dict[str, Any],
) -> str:
    idx = scene_spec["index"]
    scene_key = f"scene_{idx:02d}"
    saved_meta = manifest["scenes"].get(scene_key, {})

    if saved_meta.get("image_media_id") and (dirs["images"] / f"{scene_key}.jpg").exists():
        logger.info("[PHA 1 CACHE] Cảnh #%02d đã có ảnh: %s", idx, saved_meta["image_media_id"])
        return saved_meta["image_media_id"]

    logger.info("[PHA 1] Sinh ảnh bối cảnh Cảnh #%02d [%s]...", idx, scene_spec["title"])
    url = f"{API_BASE}/api/flow/generate-image"
    payload = {
        "prompt": scene_spec["image_prompt"],
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "character_media_ids": [BUILDER_REF, OUTPOST_REF],
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
            logger.info("✅ [PHA 1 HOÀN TẤT] Cảnh #%02d -> media_id: %s", idx, mid)
            return mid
    except Exception as exc:
        logger.exception("[LỖI PHA 1] Cảnh #%02d gặp ngoại lệ: %s", idx, exc)
        return ""


# ─── PHA 2: SINH 10 VIDEO CLIPS 8S ─────────────────────────────────────────

async def poll_video_operation(session: aiohttp.ClientSession, op_name: str, idx: int) -> Optional[str]:
    url = f"{API_BASE}/api/flow/check-status"
    start_t = time.time()
    payload = {"operations": [{"operation": {"name": op_name}, "status": "MEDIA_GENERATION_STATUS_PENDING"}]}

    while time.time() - start_t < 480:  # Timeout 8 phút
        elapsed = int(time.time() - start_t)
        try:
            async with session.post(url, json=payload, timeout=60) as resp:
                data = await resp.json()
                ops_list = data.get("operations", [])
                for op_item in ops_list:
                    item_op = op_item.get("operation", {})
                    name = item_op.get("name") or op_item.get("name")
                    status = op_item.get("status")
                    if name == op_name and status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                        meta_video = item_op.get("metadata", {}).get("video", {})
                        vid_url = meta_video.get("fifeUrl") or meta_video.get("url")
                        if vid_url:
                            logger.info("🎉 [PHA 2 HOÀN TẤT] Cảnh #%02d render xong sau %ds!", idx, elapsed)
                            return vid_url
        except Exception as exc:
            logger.warning("[POLL Cảnh #%02d] Thử lại sau 10s (%s)", idx, exc)

        logger.info("⏳ [%ds] Cảnh #%02d đang render...", elapsed, idx)
        await asyncio.sleep(12)
    return None


async def generate_scene_video(
    session: aiohttp.ClientSession,
    scene_spec: Dict[str, Any],
    dirs: Dict[str, Path],
    manifest: Dict[str, Any],
) -> bool:
    idx = scene_spec["index"]
    scene_key = f"scene_{idx:02d}"
    saved_meta = manifest["scenes"].get(scene_key, {})
    clip_path = dirs["clips"] / f"{scene_key}.mp4"

    if saved_meta.get("video_completed") and clip_path.exists():
        logger.info("[PHA 2 CACHE] Cảnh #%02d đã có clip video.", idx)
        return True

    start_img_id = saved_meta.get("image_media_id")
    if not start_img_id:
        logger.error("[LỖI] Cảnh #%02d thiếu image_media_id!", idx)
        return False

    logger.info("[PHA 2] Gửi yêu cầu sinh Video Cảnh #%02d [%s]...", idx, scene_spec["title"])
    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": start_img_id,
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
            if not ops:
                logger.error("[LỖI PHA 2] Không lấy được operation cho Cảnh #%02d: %s", idx, data)
                return False

            op_name = ops[0].get("operation", {}).get("name") or ops[0].get("name")
            logger.info("Đã gửi Cảnh #%02d. Operation: %s. Đang chờ render...", idx, op_name)

            vid_url = await poll_video_operation(session, op_name, idx)
            if vid_url:
                urllib.request.urlretrieve(vid_url, str(clip_path))
                saved_meta["video_url"] = vid_url
                saved_meta["video_completed"] = True
                saved_meta["video_file"] = str(clip_path)
                manifest["scenes"][scene_key] = saved_meta
                save_manifest(dirs["manifest"], manifest)
                return True
    except Exception as exc:
        logger.exception("[LỖI PHA 2] Cảnh #%02d sinh video thất bại: %s", idx, exc)
    return False


# ─── PHA 3: GHÉP NỐI MASTER VIDEO 80S (OPENCV) ─────────────────────────────

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
    manifest = load_manifest(dirs["manifest"])
    logger.info("=== BẮT ĐẦU PIPELINE 10 PHÂN CẢNH (80S) NÂNG CẤP CÔNG TRÌNH ===")

    async with aiohttp.ClientSession() as session:
        # PHA 1: Sinh trước toàn bộ 10 ảnh bối cảnh (Image-First Consistency)
        logger.info(">>> BẮT ĐẦU PHA 1: SINH TOÀN BỘ 10 ẢNH BỐI CẢNH ĐỒNG BỘ <<<")
        for sc in SCENES_DEF:
            await generate_scene_image(session, sc, dirs, manifest)
            await asyncio.sleep(2)

        # PHA 2: Sinh 10 Video Clips (8s) dùng ảnh làm điểm tựa
        logger.info(">>> BẮT ĐẦU PHA 2: SINH 10 VIDEO CLIPS 8S DÙNG IMAGE-TO-VIDEO <<<")
        for sc in SCENES_DEF:
            success = await generate_scene_video(session, sc, dirs, manifest)
            if not success:
                logger.warning("Cảnh #%02d không thành công, tiếp tục cảnh kế tiếp...", sc["index"])
            await asyncio.sleep(3)

    # PHA 3: Ghép nối thành phẩm 80s
    stitch_master_video(dirs)
    logger.info("=== HOÀN TẤT TRỌN VẸN PIPELINE 10 PHÂN CẢNH ===")


if __name__ == "__main__":
    asyncio.run(main())

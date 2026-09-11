"""Pipeline Song Song (Parallel Execution) 10 Phân Cảnh (80 Giây, x2) Nông Trại Tiến Hóa 3D Pixar.
Dự án mới: 303ef07c-8823-46eb-9f89-19927649cf1d
Đặc điểm:
- Sinh ảnh song song (Parallel Image Generation với Semaphore)
- Sinh video 8s song song (Parallel Video Generation với Semaphore)
- x2 biến thể cho mỗi prompt (2 candidates)
- KHÔNG tải ảnh về xóa watermark
- KHÔNG tải video về máy
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
import aiohttp

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_DIR = SCRIPT_DIR.parent
API_BASE = "http://127.0.0.1:8100"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("farm_parallel_80s")

PROJECT_ID = "303ef07c-8823-46eb-9f89-19927649cf1d"
CHAR_MEDIA_ID = "23e6e957-e23f-4c43-aec4-bba46079a661"

SCENES_DEF = [
    {
        "index": 1,
        "title": "01_Khao_Sat_Va_Dat_Mong_Ngoc",
        "image_prompt": (
            "3D Pixar style animation, cinematic vibrant daylight. Isometric wide angle view of an arid rugged farm plot with dry soil. "
            "A cartoon farmer in denim overalls and straw hat is plowing the ground with a rustic wooden plow. "
            "A radiant glowing turquoise crystal gemstone is partially buried in the freshly turned dirt, emitting soft cyan sparkles. "
            "High quality 3D stylized game render, cheerful atmosphere, NO text, NO watermark."
        ),
        "video_prompt": (
            "0-3s: The farmer pushes the rustic wooden plow through the hard soil, churning up dry dirt clods as camera tracks alongside him. "
            "3-6s: The plow blade hits something solid and uncovers a glowing turquoise gemstone that pulses with radiant cyan light. "
            "6-8s: The farmer stops in awe, wiping his brow with a joyful smile as cyan sparkles illuminate his face and the surrounding soil. NO text, NO numbers."
        ),
    },
    {
        "index": 2,
        "title": "02_Nhat_Ngoc_Va_Hoi_Sinh_Dat",
        "image_prompt": (
            "3D Pixar style animation, vibrant colors, magical daylight. Medium isometric view of the farmer kneeling down and picking up a glowing turquoise energy crystal in his hands. "
            "Concentric waves of sparkling green and golden light ripple across the plowed soil, instantly turning dry earth into rich fertile dark loam with tiny green grass sprouts popping up. "
            "Stylized 3D cartoon render, NO text, NO letters."
        ),
        "video_prompt": (
            "0-3s: The farmer bends down and lifts the glowing turquoise crystal into his hands with excitement. "
            "3-6s: A circular shockwave of sparkling green magic pulses outward from the gem, causing the barren dirt to instantly transform into dark rich fertile soil with tiny green sprouts popping up everywhere. "
            "6-8s: The farmer stands up triumphantly holding the humming gem aloft as camera pans up smoothly. NO text, NO numbers."
        ),
    },
    {
        "index": 3,
        "title": "03_Chat_Go_Va_Nang_Cap_Cuoc_Sat",
        "image_prompt": (
            "3D Pixar style animation, bright cheerful sunlight. Isometric angle of the edge of the farm clearing. "
            "A stack of glowing golden timber logs and neat wooden planks neatly assembled. "
            "The farmer holds a newly upgraded gleaming silver iron hoe with polished oak handle, radiating a golden level-up sparkle aura. "
            "Stylized 3D mobile game aesthetic, crisp render, NO text, NO words."
        ),
        "video_prompt": (
            "0-3s: The farmer swings his axe at a fallen log, and with a cheerful cartoon pop the log splits into neat stacks of polished lumber planks that float into place. "
            "3-6s: His old rustic wooden hoe begins to vibrate with golden sparkles, morphing smoothly into a gleaming polished iron hoe with a sturdy carved handle. "
            "6-8s: The farmer tests the balanced weight of the new iron hoe with a confident swing, a bright star sparkle glistening on the metal blade. NO text, NO numbers."
        ),
    },
    {
        "index": 4,
        "title": "04_Xoi_Dat_Va_Thuy_Loi_Kenh_Nuoc",
        "image_prompt": (
            "3D Pixar style animation, vibrant blue and green tones, sunny sky. Isometric view of neat symmetrical irrigation canals lined with smooth cobblestone borders traversing through the fertile farm plots. "
            "Crystal clear water flows briskly through the channels. The farmer proudly stands near the water sluice gate. "
            "Crisp 3D animation render, NO text, NO letters."
        ),
        "video_prompt": (
            "0-3s: The farmer strikes the ground with his iron hoe in rapid rhythmic motions, effortlessly carving deep straight furrows through the rich dark soil. "
            "3-6s: Smooth stone pavers snap into the ditch edges, forming a neat irrigation canal as crystal clear water gushes through with splashing cartoon ripples. "
            "6-8s: Water fills the entire network of furrows, reflecting the blue sky as camera pans along the newly irrigated agricultural grid. NO text, NO numbers."
        ),
    },
    {
        "index": 5,
        "title": "05_Gieo_Hat_Va_Lua_Than_Vuon_Cao",
        "image_prompt": (
            "3D Pixar style animation, golden hour warm lighting. Isometric view of lush thriving farmland filled with giant golden wheat stalks swaying gently. "
            "Glowing golden pollen particles drift in the air. The farmer stands among the bumper crop, smiling warmly. "
            "Rich vibrant textures, stylized 3D diorama render, NO text, NO letters."
        ),
        "video_prompt": (
            "0-3s: The farmer scatters a handful of glowing golden seeds across the moist soil bed with a sweeping arm gesture. "
            "3-6s: Green shoots burst from the earth in fast forward time-lapse, rapidly growing thick stalks and blooming into giant golden wheat ears that sway heavily. "
            "6-8s: Golden pollen particles float in the warm breeze as the farmer walks through the golden sea of wheat, marveling at the abundance. NO text, NO numbers."
        ),
    },
    {
        "index": 6,
        "title": "06_Thu_Hoach_Va_Hang_Rao_Trang",
        "image_prompt": (
            "3D Pixar style animation, cheerful daytime lighting. Isometric angle of the farm perimeter. "
            "A pristine white picket fence with polished cedar posts borders the lush field. "
            "Neatly tied sheaves of golden wheat and wooden supply crates sit stacked by the gate. "
            "Stylized 3D cartoon render, NO text, NO watermark."
        ),
        "video_prompt": (
            "0-3s: The farmer swings a gleaming scythe, neatly reaping wheat into compact golden sheaves with satisfying swoosh particle effects. "
            "3-6s: Fresh white picket fence posts automatically sprout from the ground along the property boundary, clicking together with cartoon dust puffs. "
            "6-8s: A charming wooden farm gate with a brass latch swings closed and locks snugly, establishing a secure neat perimeter. NO text, NO numbers."
        ),
    },
    {
        "index": 7,
        "title": "07_Lap_Rap_Coi_Xay_Gio_Khong_Lo",
        "image_prompt": (
            "3D Pixar style animation, sunny breezy atmosphere. Isometric view of a majestic storybook windmill with white stone base, timber framing, and large spinning canvas blades. "
            "Interlocking wooden cogs turn smoothly. The farmer stands beside the windmill entrance with hands on his hips. "
            "Stylized 3D architecture, NO text, NO letters."
        ),
        "video_prompt": (
            "0-3s: Circular white stone masonry rings stack upward to form a sturdy windmill tower as the farmer directs the placement. "
            "3-6s: A conical timber roof drops into place, and four large wooden blades with white sail canvas unfold and begin spinning smoothly in the mountain breeze. "
            "6-8s: Camera tilts upward admiring the turning sails against fluffy white cartoon clouds as wooden gears click inside. NO text, NO numbers."
        ),
    },
    {
        "index": 8,
        "title": "08_Nang_Cap_Nha_Nong_Trai_2_Tang",
        "image_prompt": (
            "3D Pixar style animation, cozy inviting sunlight. Isometric view of a beautiful two-story countryside farmhouse with warm red terracotta tile roof, "
            "white plaster walls, wooden balcony adorned with blooming red geranium flower boxes, and a stone chimney curling white smoke. "
            "Stylized 3D diorama render, NO text, NO letters."
        ),
        "video_prompt": (
            "0-3s: The small rustic wooden shack vibrates with level-up energy and expands upward into a solid two-story framework. "
            "3-6s: Hundreds of glossy red clay roof tiles cascade across the pitched roof while flower boxes full of vibrant blossoms snap onto the sunny balcony railing. "
            "6-8s: Warm yellow light glows from the paned glass windows as gentle white cartoon smoke rings puff from the stone chimney. NO text, NO numbers."
        ),
    },
    {
        "index": 9,
        "title": "09_May_Keo_Co_Khi_Va_Dong_Co",
        "image_prompt": (
            "3D Pixar style animation, dynamic action shot, bright sunshine. Isometric view of the farmer driving a charming chunky green and yellow cartoon tractor across vast green pasture. "
            "In the background, chubby stylized spotted dairy cows graze peacefully beside a wooden red barn. "
            "Stylized 3D game render, NO text, NO words."
        ),
        "video_prompt": (
            "0-3s: The farmer hops into the seat of a chunky cartoon steam tractor with oversized tread wheels and pulls the brass starter lever. "
            "3-6s: The tractor chugs forward happily, puffing tiny steam clouds as its rear cultivator attachments smoothly groom wide rows of green pasture. "
            "6-8s: Chubby black-and-white cartoon cows graze happily by a newly erected red barn as the tractor rolls past. NO text, NO numbers."
        ),
    },
    {
        "index": 10,
        "title": "10_Dai_Canh_Nong_Trai_Thinh_Vuong",
        "image_prompt": (
            "3D Pixar style animation, majestic golden hour panorama, cinematic lighting. Wide isometric grand view of the ultimate flourishing fantasy farm diorama. "
            "Two-story red-roof farmhouse, spinning white windmill, shimmering golden wheat fields, flowing blue irrigation canals, green pasture with grazing cows, and lush orchards. "
            "Colorful celebratory confetti and sparkling golden upgrade fireworks in the sky. Masterpiece 3D render, NO text, NO watermark."
        ),
        "video_prompt": (
            "0-3s: The camera performs an epic, sweeping orbital pan across the fully upgraded paradise farm, capturing the harmonious motion of windmill, flowing canals, and golden crops. "
            "3-6s: Colorful celebratory cartoon fireworks and golden star sparkles burst cheerfully across the sunny blue sky above the farmhouse. "
            "6-8s: The farmer stands at the front gate, waving joyfully with both hands toward the camera as the whole farm gleams in vibrant golden sunlight. NO text, NO numbers."
        ),
    },
]

MANIFEST_FILE = AGENT_DIR / "output" / "farm_upgrade_80s_parallel.json"


def load_manifest() -> Dict[str, Any]:
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "project_id": PROJECT_ID,
        "character_media_id": CHAR_MEDIA_ID,
        "video_id": "",
        "scenes": {}
    }


def save_manifest(data: Dict[str, Any]):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


async def setup_video_and_scenes(session: aiohttp.ClientSession, manifest: Dict[str, Any]) -> str:
    """Tạo video container và 10 scenes trong SQLite database nếu chưa có."""
    vid = manifest.get("video_id")
    if not vid:
        logger.info("Khởi tạo Video container mới trong Project %s...", PROJECT_ID)
        url = f"{API_BASE}/api/videos"
        payload = {
            "project_id": PROJECT_ID,
            "title": "Nông Trại Tiến Hóa 80s: Cày Ruộng Nâng Cấp 3D",
            "orientation": "HORIZONTAL"
        }
        try:
            async with session.post(url, json=payload) as resp:
                vdata = await resp.json()
                vid = vdata.get("id")
                manifest["video_id"] = vid
                logger.info("✅ Đã tạo Video ID: %s", vid)
        except Exception as e:
            logger.error("Lỗi tạo video: %s", e)

    # Đăng ký 10 scenes
    for sc in SCENES_DEF:
        idx = sc["index"]
        skey = f"scene_{idx:02d}"
        sinfo = manifest["scenes"].setdefault(skey, {})
        if not sinfo.get("scene_id") and vid:
            url = f"{API_BASE}/api/scenes"
            payload = {
                "video_id": vid,
                "display_order": idx,
                "prompt": sc["image_prompt"],
                "video_prompt": sc["video_prompt"],
                "character_names": ["Farmer_Dan"],
                "duration": 8,
                "chain_type": "ROOT"
            }
            try:
                async with session.post(url, json=payload) as resp:
                    sc_data = await resp.json()
                    sinfo["scene_id"] = sc_data.get("id")
                    sinfo["title"] = sc["title"]
            except Exception as e:
                logger.error("Lỗi tạo scene %d: %s", idx, e)

    save_manifest(manifest)
    return vid


async def generate_single_image(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    sc: Dict[str, Any],
    variant: int,
    manifest: Dict[str, Any]
):
    """Sinh 1 ảnh candidate với Semaphore kiểm soát số lượng luồng song song."""
    idx = sc["index"]
    skey = f"scene_{idx:02d}"
    sinfo = manifest["scenes"].setdefault(skey, {})
    mid_key = f"image_media_id_{variant}"

    if sinfo.get(mid_key):
        logger.info("[Cảnh #%02d] Đã có sẵn ảnh Candidate #%d: %s", idx, variant, sinfo[mid_key])
        return sinfo[mid_key]

    async with sem:
        logger.info("🚀 [SONG SONG] Bắt đầu sinh Cảnh #%02d - Candidate #%d [%s]...", idx, variant, sc["title"])
        url = f"{API_BASE}/api/flow/generate-image"
        payload = {
            "prompt": sc["image_prompt"],
            "project_id": PROJECT_ID,
            "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "user_paygate_tier": "PAYGATE_TIER_TWO",
            "character_media_ids": [CHAR_MEDIA_ID]
        }

        for attempt in range(3):
            try:
                async with session.post(url, json=payload, timeout=90) as resp:
                    data = await resp.json()
                    media_list = data.get("media", [])
                    if media_list:
                        m = media_list[0]
                        mid = m.get("name") or m.get("id")
                        sinfo[mid_key] = mid
                        # Gán ảnh chính nếu chưa có
                        if not sinfo.get("image_media_id"):
                            sinfo["image_media_id"] = mid
                        logger.info("✨ [XONG ẢNH] Cảnh #%02d - Candidate #%d -> %s", idx, variant, mid)
                        save_manifest(manifest)
                        return mid
            except Exception as e:
                logger.warning("[Cảnh #%02d - Var %d] Lỗi thử lại (%d/3): %s", idx, variant, attempt + 1, e)
            await asyncio.sleep(3)

    return None


async def generate_single_video(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    sc: Dict[str, Any],
    variant: int,
    manifest: Dict[str, Any]
):
    """Gửi yêu cầu sinh 1 video 8s song song với Semaphore."""
    idx = sc["index"]
    skey = f"scene_{idx:02d}"
    sinfo = manifest["scenes"].setdefault(skey, {})
    op_key = f"video_op_{variant}"

    if sinfo.get(op_key):
        logger.info("[Cảnh #%02d] Đã có video operation Candidate #%d: %s", idx, variant, sinfo[op_key])
        return sinfo[op_key]

    start_img = sinfo.get(f"image_media_id_{variant}") or sinfo.get("image_media_id_1") or sinfo.get("image_media_id")
    if not start_img:
        logger.warning("[Cảnh #%02d] Chưa có ảnh để sinh video #%d", idx, variant)
        return None

    async with sem:
        logger.info("🎬 [SONG SONG] Bắt đầu sinh Video 8s Cảnh #%02d - Candidate #%d...", idx, variant)
        url = f"{API_BASE}/api/flow/generate-video"
        payload = {
            "start_image_media_id": start_img,
            "prompt": sc["video_prompt"],
            "project_id": PROJECT_ID,
            "scene_id": sinfo.get("scene_id", f"scene_{idx:02d}"),
            "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "user_paygate_tier": "PAYGATE_TIER_TWO",
            "duration": 8.0,
            "duration_s": 8,
            "title": f"Scene_{idx:02d}_Var{variant}_{sc['title']}"
        }

        try:
            async with session.post(url, json=payload, timeout=90) as resp:
                data = await resp.json()
                ops = data.get("operations", [])
                if ops:
                    op_name = ops[0].get("operation", {}).get("name") or ops[0].get("name")
                    sinfo[op_key] = op_name
                    logger.info("🎉 [KHỞI TẠO VIDEO] Cảnh #%02d - Candidate #%d -> Operation: %s", idx, variant, op_name)
                    save_manifest(manifest)
                    return op_name
                else:
                    logger.error("[Cảnh #%02d - Var %d] Lỗi sinh video: %s", idx, variant, data)
        except Exception as e:
            logger.error("[Cảnh #%02d - Var %d] Ngoại lệ sinh video: %s", idx, variant, e)

    return None


async def main():
    logger.info("==============================================================================")
    logger.info("BẮT ĐẦU PIPELINE SONG SONG 10 CẢNH NÔNG TRẠI 3D (80S, MỖI PROMPT 8S, X2)")
    logger.info("Dự án mới: %s", PROJECT_ID)
    logger.info("Nhân vật tham chiếu: %s", CHAR_MEDIA_ID)
    logger.info("==============================================================================")

    manifest = load_manifest()

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Bước 1: Setup Video & 10 Scenes
        await setup_video_and_scenes(session, manifest)

        # Bước 2: Sinh ảnh SONG SONG (3 luồng đồng thời, x2 candidates = 20 ảnh)
        logger.info("\n>>> BƯỚC 2: KÍCH HOẠT SINH ẢNH SONG SONG CHO 10 CẢNH (X2 CANDIDATES) <<<")
        img_sem = asyncio.Semaphore(3)  # Chạy 3 luồng song song
        img_tasks = []
        for sc in SCENES_DEF:
            for var in (1, 2):
                img_tasks.append(generate_single_image(session, img_sem, sc, var, manifest))

        await asyncio.gather(*img_tasks)
        logger.info("✅ HOÀN TẤT TOÀN BỘ ẢNH BỐI CẢNH SONG SONG (20 ẢNH)")

        # Bước 3: Sinh video 8s SONG SONG (3 luồng đồng thời, x2 candidates = 20 video ops)
        logger.info("\n>>> BƯỚC 3: KÍCH HOẠT SINH VIDEO 8S SONG SONG CHO 10 CẢNH (X2 CANDIDATES) <<<")
        vid_sem = asyncio.Semaphore(3)  # Chạy 3 luồng song song
        vid_tasks = []
        for sc in SCENES_DEF:
            for var in (1, 2):
                vid_tasks.append(generate_single_video(session, vid_sem, sc, var, manifest))

        await asyncio.gather(*vid_tasks)
        logger.info("✅ HOÀN TẤT KÍCH HOẠT TOÀN BỘ 20 VIDEO 8S TRÊN GOOGLE FLOW!")

    save_manifest(manifest)
    logger.info("\n==============================================================================")
    logger.info("🎉 TOÀN BỘ PIPELINE ĐÃ ĐƯỢC KÍCH HOẠT THÀNH CÔNG TRÊN GOOGLE FLOW!")
    logger.info("Manifest kết quả lưu tại: %s", MANIFEST_FILE)
    logger.info("==============================================================================")


if __name__ == "__main__":
    asyncio.run(main())

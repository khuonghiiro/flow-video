"""Script tự động hóa pipeline 10 phân cảnh (80 giây, mỗi prompt 8s, x2)
Nông trại tiến hóa: Bác nông dân cày ruộng, nhặt nguyên liệu nâng cấp nông trại 3D Pixar.
Đặc điểm:
- Không tải ảnh về xóa watermark.
- Không tải video về máy.
- Sinh x2 biến thể cho mỗi prompt (ảnh và video).
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
logger = logging.getLogger("farm_upgrade_80s")

PROJECT_DATA = {
    "name": "Nông Trại Tiến Hóa 3D: Cày Ruộng Nâng Cấp Nông Trại (80s)",
    "description": "Phim hoạt hình 3D phong cách Pixar chủ đề nâng cấp nông trại: Cày ruộng, nhặt nguyên liệu, nâng cấp công trình và điền trang kỳ ảo",
    "story": "Một người nông dân chăm chỉ cày xới mảnh đất khô cằn, nhặt được đá ngọc và gỗ quý, từng bước nâng cấp nông cụ, thủy lợi, cối xay gió và ngôi nhà nông trại trù phú.",
    "material": "3d_pixar",
    "language": "vi",
    "user_paygate_tier": "PAYGATE_TIER_TWO"
}

CHARACTER_DATA = {
    "name": "Farmer_Dan",
    "entity_type": "character",
    "description": "Bác nông dân hoạt hình 3D Pixar vui vẻ, khuôn mặt đôn hậu tươi cười, đội mũ rơm vàng, mặc áo yếm bò xanh denim bên ngoài áo sơ mi kẻ caro đỏ, đi ủng da nâu, vóc dáng hoạt bát khỏe khoắn.",
    "image_prompt": (
        "3D animated Pixar-quality character design portrait of Farmer Dan, a cheerful hardworking cartoon farmer, "
        "warm smiling face with bright eyes, wearing a rustic straw hat, classic blue denim dungaree overalls over a red plaid flannel shirt, "
        "and sturdy brown work boots. Clean vibrant 3D stylized render, cinematic daylight, character concept art, NO text, NO watermark, solid neutral background."
    )
}

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

MANIFEST_FILE = AGENT_DIR / "output" / "farm_upgrade_80s_manifest.json"


def load_manifest() -> Dict[str, Any]:
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"project_id": "", "character": {}, "scenes": {}}


def save_manifest(data: Dict[str, Any]):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


async def init_project_and_character(session: aiohttp.ClientSession, manifest: Dict[str, Any]) -> str:
    """Khởi tạo hoặc tải Project và Character trên backend."""
    proj_id = manifest.get("project_id")
    if not proj_id:
        # Sử dụng flow project id đang kết nối hoặc tạo mới
        proj_id = "f762d7dd-63d3-4a43-a5bc-6c3fb2072839"  # Project flow đã được xác nhận hoạt động
        manifest["project_id"] = proj_id
        save_manifest(manifest)
        logger.info("Sử dụng Flow Project ID: %s", proj_id)

    # Sinh ảnh tham chiếu nhân vật (x2)
    char_meta = manifest.get("character", {})
    if not char_meta.get("media_id_1"):
        logger.info(">>> Đang sinh ảnh tham chiếu nhân vật Farmer_Dan (x2)...")
        for variant in (1, 2):
            url = f"{API_BASE}/api/flow/generate-image"
            payload = {
                "prompt": CHARACTER_DATA["image_prompt"],
                "project_id": proj_id,
                "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
                "user_paygate_tier": "PAYGATE_TIER_TWO"
            }
            try:
                async with session.post(url, json=payload, timeout=90) as resp:
                    data = await resp.json()
                    media_list = data.get("media", [])
                    if media_list:
                        m = media_list[0]
                        mid = m.get("name") or m.get("id")
                        char_meta[f"media_id_{variant}"] = mid
                        logger.info("✅ Farmer_Dan Candidate #%d -> media_id: %s", variant, mid)
            except Exception as e:
                logger.error("Lỗi sinh ảnh nhân vật #%d: %s", variant, e)
            await asyncio.sleep(2)

        char_meta["media_id"] = char_meta.get("media_id_1") or char_meta.get("media_id_2")
        manifest["character"] = char_meta
        save_manifest(manifest)

    return proj_id


async def generate_scene_images_x2(
    session: aiohttp.ClientSession,
    proj_id: str,
    char_media_id: str,
    sc: Dict[str, Any],
    manifest: Dict[str, Any]
):
    """Sinh x2 ảnh bối cảnh cho 1 cảnh trực tiếp trên Flow."""
    idx = sc["index"]
    scene_key = f"scene_{idx:02d}"
    sdata = manifest["scenes"].setdefault(scene_key, {})

    for variant in (1, 2):
        key_mid = f"image_media_id_{variant}"
        if sdata.get(key_mid):
            logger.info("[Cảnh #%02d] Đã có ảnh Candidate #%d: %s", idx, variant, sdata[key_mid])
            continue

        logger.info("[Cảnh #%02d] Đang sinh ảnh Candidate #%d [%s]...", idx, variant, sc["title"])
        url = f"{API_BASE}/api/flow/generate-image"
        payload = {
            "prompt": sc["image_prompt"],
            "project_id": proj_id,
            "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "user_paygate_tier": "PAYGATE_TIER_TWO",
        }
        if char_media_id:
            payload["character_media_ids"] = [char_media_id]

        for attempt in range(3):
            try:
                async with session.post(url, json=payload, timeout=90) as resp:
                    data = await resp.json()
                    media_list = data.get("media", [])
                    if media_list:
                        m = media_list[0]
                        mid = m.get("name") or m.get("id")
                        sdata[key_mid] = mid
                        logger.info("✅ [Cảnh #%02d] Ảnh Candidate #%d -> media_id: %s", idx, variant, mid)
                        break
                    else:
                        logger.warning("[Cảnh #%02d] Không có media trả về, thử lại...", idx)
            except Exception as e:
                logger.warning("[Cảnh #%02d] Lỗi sinh ảnh (lần %d/3): %s", idx, attempt + 1, e)
            await asyncio.sleep(3)

        save_manifest(manifest)
        await asyncio.sleep(2)


async def generate_scene_videos_x2(
    session: aiohttp.ClientSession,
    proj_id: str,
    sc: Dict[str, Any],
    manifest: Dict[str, Any]
):
    """Sinh x2 video Veo3 8s cho 1 cảnh trực tiếp trên Flow."""
    idx = sc["index"]
    scene_key = f"scene_{idx:02d}"
    sdata = manifest["scenes"].setdefault(scene_key, {})

    for variant in (1, 2):
        key_op = f"video_op_{variant}"
        if sdata.get(key_op):
            logger.info("[Cảnh #%02d] Đã gửi lệnh sinh Video Candidate #%d: %s", idx, variant, sdata[key_op])
            continue

        start_img = sdata.get(f"image_media_id_{variant}") or sdata.get("image_media_id_1")
        if not start_img:
            logger.warning("[Cảnh #%02d] Thiếu ảnh xuất phát cho video #%d, bỏ qua.", idx, variant)
            continue

        logger.info("[Cảnh #%02d] Đang gửi lệnh sinh Video 8s Candidate #%d [%s]...", idx, variant, sc["title"])
        url = f"{API_BASE}/api/flow/generate-video"
        payload = {
            "start_image_media_id": start_img,
            "prompt": sc["video_prompt"],
            "project_id": proj_id,
            "scene_id": f"sc_{idx:02d}_v{variant}",
            "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "user_paygate_tier": "PAYGATE_TIER_TWO",
            "duration": 8.0,
            "duration_s": 8,
            "title": f"Scene_{idx:02d}_Var_{variant}_{sc['title']}"
        }

        try:
            async with session.post(url, json=payload, timeout=90) as resp:
                data = await resp.json()
                ops = data.get("operations", [])
                if ops:
                    op_name = ops[0].get("operation", {}).get("name") or ops[0].get("name")
                    sdata[key_op] = op_name
                    logger.info("🎬 [Cảnh #%02d] Video Candidate #%d đã khởi tạo trên Flow! Op: %s", idx, variant, op_name)
                else:
                    logger.error("[Cảnh #%02d] Lỗi không nhận được operation: %s", idx, data)
        except Exception as e:
            logger.error("[Cảnh #%02d] Ngoại lệ khi tạo video: %s", idx, e)

        save_manifest(manifest)
        await asyncio.sleep(3)


async def main():
    logger.info("==============================================================================")
    logger.info("BẮT ĐẦU PIPELINE 10 CẢNH (80S, MỖI PROMPT 8S, X2) NÂNG CẤP NÔNG TRẠI 3D PIXAR")
    logger.info("==============================================================================")

    manifest = load_manifest()

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Bước 1: Khởi tạo Project & Sinh ảnh nhân vật (x2)
        proj_id = await init_project_and_character(session, manifest)
        char_mid = manifest.get("character", {}).get("media_id", "")
        logger.info("Dự án sẵn sàng. Character Media ID: %s", char_mid)

        # Bước 2: Sinh x2 ảnh bối cảnh cho cả 10 Scenes
        logger.info("\n>>> BƯỚC 2: SINH X2 ẢNH BỐI CẢNH CHO TOÀN BỘ 10 PHÂN CẢNH <<<")
        for sc in SCENES_DEF:
            await generate_scene_images_x2(session, proj_id, char_mid, sc, manifest)

        # Bước 3: Sinh x2 video 8s cho cả 10 Scenes
        logger.info("\n>>> BƯỚC 3: KÍCH HOẠT SINH X2 VIDEO 8S CHO TOÀN BỘ 10 PHÂN CẢNH TRÊN FLOW <<<")
        for sc in SCENES_DEF:
            await generate_scene_videos_x2(session, proj_id, sc, manifest)

    logger.info("\n==============================================================================")
    logger.info("🎉 HOÀN TẤT GỬI TOÀN BỘ YÊU CẦU SINH ẢNH & VIDEO X2 LÊN GOOGLE FLOW!")
    logger.info("Xem chi tiết trạng thái trong file: %s", MANIFEST_FILE)
    logger.info("==============================================================================")


if __name__ == "__main__":
    asyncio.run(main())

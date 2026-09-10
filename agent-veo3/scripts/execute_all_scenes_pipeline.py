"""Master Pipeline: Tự động hoá toàn bộ 10 Phân Cảnh Master (80 Giây).
Dự án: Đại Huyền Thái Sư - Hoàn Chân Bắt Tiên
Project ID: 08f70524-3b10-49d0-9b68-0b2fde61190e
Model: veo_3_1_interpolation_lite_low_priority (0 credit)

Tính năng cao cấp:
1. Frame Chaining thông minh: Tự động dùng lại End Frame của Cảnh N làm Start Frame của Cảnh N+1.
2. Khử sạch Watermark 100% bằng Reverse Alpha Blending.
3. Polling tiến độ & tự động tải clip MP4 ngay khi hoàn thành.
4. Tự động lưu tiến độ vào frame_manifest.json để có thể resume nếu gặp gián đoạn.
5. Tự động ghép nối (stitch/concat) toàn bộ 10 video thành master video 80s bằng OpenCV.
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
import cv2

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from remove_gemini_watermark import remove_watermark

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("master_pipeline")

API_BASE = "http://127.0.0.1:8100"
PROJECT_ID = "08f70524-3b10-49d0-9b68-0b2fde61190e"
MOVIE_SLUG = "dai_huyen_thai_su"


def setup_directories(slug: str) -> Dict[str, Path]:
    base_dir = SCRIPT_DIR.parent / "output" / "movies" / slug
    raw_dir = base_dir / "watermarks"
    cleaned_dir = base_dir / "cleaned"
    clips_dir = base_dir / "clips"
    frames_dir = base_dir / "motion_frames"

    for d in (base_dir, raw_dir, cleaned_dir, clips_dir, frames_dir):
        d.mkdir(parents=True, exist_ok=True)

    return {
        "base": base_dir,
        "raw": raw_dir,
        "cleaned": cleaned_dir,
        "clips": clips_dir,
        "frames": frames_dir,
        "manifest": base_dir / "frame_manifest.json",
    }


async def check_health(session: aiohttp.ClientSession) -> bool:
    url = f"{API_BASE}/health"
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("extension_connected", False):
                    logger.info("Pre-flight Health Check OK (Extension Connected: True)")
                    return True
                logger.error("Extension chưa kết nối!")
    except Exception as e:
        logger.error("Không thể kết nối đến Backend: %s", e)
    return False


async def generate_and_clean_image(
    session: aiohttp.ClientSession,
    project_id: str,
    tag: str,
    prompt: str,
    dirs: Dict[str, Path],
    cache_dict: Dict[str, str],
) -> str:
    """Sinh ảnh, tải về, khử watermark và upload lại để lấy clean Media UUID."""
    if tag in cache_dict:
        logger.info("[CACHE HIT] Dùng lại Media UUID đã có cho '%s': %s", tag, cache_dict[tag])
        return cache_dict[tag]

    logger.info("[SINH ẢNH] Gửi prompt tạo ảnh cho '%s'...", tag)
    url = f"{API_BASE}/api/flow/generate-image"
    payload = {
        "prompt": prompt,
        "project_id": project_id,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "title": f"{MOVIE_SLUG}_{tag}",
    }

    # Sinh ảnh với cơ chế retry 3 lần chống đứt kết nối
    t0 = time.time()
    data = None
    last_err = None
    for attempt in range(1, 4):
        try:
            async with session.post(url, json=payload, timeout=240) as resp:
                data = await resp.json()
                if resp.status == 200:
                    break
                last_err = data
        except Exception as e:
            last_err = str(e)
        logger.warning("  [Thử lại %d/3] Sinh ảnh '%s' gặp sự cố: %s. Chờ 3s...", attempt, tag, last_err)
        await asyncio.sleep(3)

    if not data or not isinstance(data, dict):
        raise RuntimeError(f"Lỗi sinh ảnh '{tag}' sau 3 lần thử: {last_err}")


    media_list = data.get("media", [])
    if not media_list and isinstance(data.get("data"), dict):
        media_list = data["data"].get("media", [])

    url_found = None
    if media_list and isinstance(media_list, list):
        item = media_list[0]
        img_block = item.get("image", {})
        gen_img = img_block.get("generatedImage", {}) if isinstance(img_block, dict) else {}
        url_found = gen_img.get("fifeUrl") or img_block.get("fifeUrl") or item.get("fifeUrl")

    if not url_found:
        raise RuntimeError(f"Không tìm thấy URL ảnh cho '{tag}': {data}")

    raw_path = dirs["raw"] / f"{tag}_raw.png"
    clean_path = dirs["cleaned"] / f"{tag}_clean.png"

    # Tải ảnh thô về
    async with session.get(url_found, timeout=60) as img_resp:
        if img_resp.status == 200:
            raw_path.write_bytes(await img_resp.read())
        else:
            raise RuntimeError(f"Tải ảnh thô thất bại HTTP {img_resp.status}")

    # Khử logo watermark
    img = cv2.imread(str(raw_path))
    if img is None:
        raise RuntimeError(f"Không thể đọc file ảnh: {raw_path}")
    cleaned = remove_watermark(img, aggressive=False)
    cv2.imwrite(str(clean_path), cleaned, [int(cv2.IMWRITE_PNG_COMPRESSION), 3])
    logger.info("Đã khử logo cho '%s' -> %s", tag, clean_path.name)

    # Upload ảnh sạch lên Google Flow với cơ chế retry tối đa 3 lần
    logger.info("[UPLOAD SẠCH] Uploading '%s' lên Flow...", clean_path.name)
    upload_url = f"{API_BASE}/api/flow/upload-image"
    upload_payload = {
        "file_path": str(clean_path.resolve()),
        "project_id": project_id,
        "file_name": clean_path.name,
    }

    new_uuid = None
    last_err = None
    for attempt in range(1, 4):
        try:
            async with session.post(upload_url, json=upload_payload, timeout=60) as up_resp:
                up_data = await up_resp.json()
                new_uuid = up_data.get("media_id") or up_data.get("mediaId")
                if not new_uuid and isinstance(up_data.get("raw"), dict):
                    raw = up_data["raw"]
                    new_uuid = raw.get("name") or raw.get("id") or raw.get("_mediaId")
                    if not new_uuid and isinstance(raw.get("media"), dict):
                        new_uuid = raw["media"].get("name") or raw["media"].get("id")

                if new_uuid:
                    break
                last_err = up_data
        except Exception as e:
            last_err = str(e)

        logger.warning("  [Thử lại %d/3] Upload '%s' chưa nhận được UUID (Lỗi: %s). Chờ 3s...", attempt, tag, last_err)
        await asyncio.sleep(3)

    if not new_uuid:
        raise RuntimeError(f"Upload ảnh sạch '{tag}' thất bại sau 3 lần thử: {last_err}")

    logger.info("Upload thành công '%s'! Clean Media UUID: %s", tag, new_uuid)
    cache_dict[tag] = new_uuid
    return new_uuid



def extract_op_id(video_res: Dict[str, Any]) -> str:
    """Trích xuất ID operation an toàn."""
    if not isinstance(video_res, dict):
        return ""
    for container in [video_res, video_res.get("data", {})]:
        if not isinstance(container, dict):
            continue
        ops = container.get("operations", [])
        if ops and isinstance(ops, list) and len(ops) > 0:
            first = ops[0]
            if isinstance(first, dict):
                op_obj = first.get("operation")
                if isinstance(op_obj, dict) and "name" in op_obj:
                    return str(op_obj["name"])
                if "name" in first:
                    return str(first["name"])
        op = container.get("operation")
        if isinstance(op, dict) and "name" in op:
            return str(op["name"])

    def find_op(obj):
        if isinstance(obj, dict):
            if "name" in obj and isinstance(obj["name"], str):
                v = obj["name"]
                if len(v) == 36 and v.count("-") == 4:
                    return v
                if "operations/" in v:
                    return v
            for val in obj.values():
                res = find_op(val)
                if res:
                    return res
        elif isinstance(obj, list):
            for it in obj:
                res = find_op(it)
                if res:
                    return res
        return None

    return find_op(video_res) or video_res.get("operationId") or video_res.get("id") or ""


async def poll_video_ready(
    session: aiohttp.ClientSession,
    project_id: str,
    operation_id: str,
    scene_idx: int,
    max_wait_seconds: int = 480,
) -> Dict[str, Any]:
    url = f"{API_BASE}/api/flow/check-status"
    payload = {
        "operations": [{"operation": {"name": operation_id}}],
        "project_id": project_id,
    }
    start_time = time.time()
    attempt = 0

    while time.time() - start_time < max_wait_seconds:
        attempt += 1
        await asyncio.sleep(10)
        try:
            async with session.post(url, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    continue
                res = await resp.json()
                ops = res.get("operations", [])
                if not ops:
                    continue
                entry = ops[0]
                status = entry.get("status")
                elapsed = time.time() - start_time
                logger.info("  [Cảnh %02d Polling] (+%.0fs) Status: %s", scene_idx, elapsed, status)

                if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                    meta_video = entry.get("operation", {}).get("metadata", {}).get("video", {})
                    video_url = meta_video.get("fifeUrl") or meta_video.get("url")
                    media_id = meta_video.get("mediaId") or operation_id
                    return {
                        "status": "SUCCESSFUL",
                        "media_id": media_id,
                        "video_url": video_url,
                        "elapsed_s": elapsed,
                    }
                elif status in ("MEDIA_GENERATION_STATUS_FAILED", "MEDIA_GENERATION_STATUS_REJECTED"):
                    return {"status": status, "error": entry.get("error")}
        except Exception as e:
            logger.warning("  [Cảnh %02d] Polling network warning: %s", scene_idx, e)

    raise TimeoutError(f"Hết thời gian chờ video Cảnh {scene_idx} ({operation_id})")


def extract_motion_frames(video_path: Path, output_dir: Path, scene_idx: int, timestamps: List[float]):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for ts in timestamps:
        target_frame = min(int(ts * fps), total_frames - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        if ret:
            out_file = output_dir / f"scene{scene_idx:02d}_motion_{int(ts):02d}s.png"
            cv2.imwrite(str(out_file), frame)
    cap.release()


def concat_all_scenes_opencv(clips: List[Path], output_path: Path):
    """Ghép nối tất cả các clip MP4 thành một video master duy nhất bằng OpenCV."""
    logger.info("=" * 70)
    logger.info("[GHÉP NỐI MASTER] Đang ghép %d clip video...", len(clips))
    logger.info("=" * 70)

    if not clips:
        logger.error("Không có clip nào để ghép!")
        return

    first_cap = cv2.VideoCapture(str(clips[0]))
    width = int(first_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(first_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = first_cap.get(cv2.CAP_PROP_FPS) or 24.0
    first_cap.release()

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    total_stitched_frames = 0
    for idx, clip in enumerate(clips, 1):
        cap = cv2.VideoCapture(str(clip))
        clip_frames = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            clip_frames += 1
            total_stitched_frames += 1
        cap.release()
        logger.info("  Đã ghép Clip #%02d (%s): %d frames", idx, clip.name, clip_frames)

    out.release()
    total_duration = total_stitched_frames / fps
    logger.info("MASTER VIDEO HOÀN TẤT: %s", output_path.name)
    logger.info("  Tổng số frames: %d | Thời lượng: %.1f giây", total_stitched_frames, total_duration)


async def main():
    dirs = setup_directories(MOVIE_SLUG)
    logger.info("=" * 80)
    logger.info("  BẮT ĐẦU PIPELINE TỰ ĐỘNG KẾT XUẤT 10 PHÂN CẢNH MASTER (80 GIÂY)")
    logger.info("  Project ID: %s", PROJECT_ID)
    logger.info("=" * 80)

    # Đọc manifest nếu đã có
    manifest: Dict[str, Any] = {}
    if dirs["manifest"].exists():
        try:
            manifest = json.loads(dirs["manifest"].read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    media_cache: Dict[str, str] = manifest.get("media_cache", {})
    completed_clips: Dict[int, str] = manifest.get("completed_clips", {})

    # Đăng ký thông tin Cảnh 1 đã xong
    scene1_clip = dirs["clips"] / "scene_01_8s.mp4"
    if scene1_clip.exists():
        completed_clips[1] = str(scene1_clip.resolve())
        completed_clips["1"] = str(scene1_clip.resolve())
        media_cache["frame_01_tiec_tho_toan_canh"] = "e77319a1-1242-4990-aa9e-7afbeeda3a60"
        media_cache["frame_02_can_canh_ly_pham_uong_ruou"] = "868ad20d-6a0e-4f2a-98c7-0cd095dc55e5"
        media_cache["frame_03_ly_pham_balcony_look_sky"] = "889e9a1b-283d-4a0e-af2c-13a62845bf2d"


    # Định nghĩa 10 phân cảnh chi tiết
    scenes_spec = [
        # Cảnh 1 (đã xong)
        {
            "index": 1,
            "title": "Đại Tiệc Mừng Thọ 70 Tuổi",
            "start_tag": "frame_01_tiec_tho_toan_canh",
            "end_tag": "frame_02_can_canh_ly_pham_uong_ruou",
            "start_prompt": None,
            "end_prompt": None,
            "video_prompt": (
                "0-3s: Inside the opulent imperial banquet hall illuminated by glowing lanterns, the noble elderly statesman in embroidered crimson robes raises his jade wine cup with commanding dignity. Steadicam tracks slowly forward between rows of kneeling officials raising their goblets. "
                "3-6s: The elderly statesman brings the cup to his lips, gracefully drinking the fine wine in a single smooth draught, while the court officials kowtow and cheer in celebration. "
                "6-8s: Lowering the jade goblet, he gently strokes his silver beard with a proud, triumphant smile of absolute worldly power, settling smoothly into a poised triumphant sitting stance."
            ),
        },
        # Cảnh 2 (00:08 - 00:16)
        {
            "index": 2,
            "title": "Dị Tượng Rạch Trời & Báo Động",
            "start_tag": "frame_02_can_canh_ly_pham_uong_ruou",  # NỐI CHUỖI TỪ END CẢNH 1
            "end_tag": "frame_03_ly_pham_balcony_look_sky",
            "start_prompt": None,  # Tái sử dụng
            "end_prompt": (
                "A cinematic medium-wide shot of the 70-year-old noble elder statesman in crimson robes standing on an open "
                "carved wooden terrace of his palace at night. He grips the wooden balustrade looking up in shock at the stormy "
                "night sky over the ancient capital city. High in the distant dark clouds, two blinding silver comet-like light "
                "trails streak rapidly across the sky toward the city. Dramatic moonlight, lanterns fluttering in sudden wind, "
                "photorealistic 8k, 16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: Sudden shouting echoes from outside, disturbing the banquet. The elderly statesman frowns with displeased "
                "authority, firmly placing his cup onto the table and rising up from his grand carved chair. "
                "3-6s: The cheering hall falls completely silent. Camera tracks in front of him as he strides briskly past silent "
                "kneeling attendants toward the wide open wooden balcony overlooking the imperial capital. "
                "6-8s: Stepping onto the wooden terrace, he looks up toward the distant horizon in stunned awe as two blinding silver "
                "comet streaks blaze rapidly across the dark sky toward the capital."
            ),
        },
        # Cảnh 3 (00:16 - 00:24)
        {
            "index": 3,
            "title": "Hai Vị Tu Tiên Giả Đối Đầu Trên Không",
            "start_tag": "frame_03_sky_two_meteors_approaching",
            "end_tag": "frame_04_two_cultivators_hovering_lightning",
            "start_prompt": (
                "A cinematic wide exterior shot of the dark stormy night sky over ancient Xuan Jing city rooftops. "
                "Two intense silver meteor light trails streak diagonally across the storm clouds with brilliant lightning arcs, "
                "illuminating ancient Chinese tiled rooftops below. Photorealistic 8k, dramatic moody volumetric clouds, 16:9 aspect ratio."
            ),
            "end_prompt": (
                "A cinematic eye-level medium-wide shot of two immortal Daoist cultivators hovering weightlessly in mid-air above ancient "
                "city rooftops. One wears white flowing celestial robes with cold aloof gaze, the other wears ragged dark blue Taoist robes "
                "with fierce defiant grin. Ethereal spirit energy and crackling purple lightning arcs swirl around them, wide sleeves and long "
                "hair billowing dynamically in high-altitude gale winds. Photorealistic 8k, dramatic celestial contrast, 16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: Two dazzling meteoric silver light trails streak diagonally across the storm clouds above Xuan Jing city, "
                "decelerating abruptly with explosive acoustic thunderclaps. "
                "3-6s: The blinding light disperses, revealing two immortal Daoist cultivators hovering in mid-air. Ethereal spirit "
                "energy swirls around them as violent lightning bolts arc across the dark sky. "
                "6-8s: Facing each other with hostile intense gazes, their wide sleeves and long black hair billow dynamically in the "
                "storm gale, hands positioned in ready combat stances hovering poised over the tiled rooftops."
            ),
        },
        # Cảnh 4 (00:24 - 00:32)
        {
            "index": 4,
            "title": "Khấu Hồng Cuồng Nộ & Đại Vụ Nổ San Phẳng",
            "start_tag": "frame_04_two_cultivators_hovering_lightning",  # NỐI CHUỖI TỪ END CẢNH 3
            "end_tag": "frame_05_apocalyptic_crimson_explosion",
            "start_prompt": None,
            "end_prompt": (
                "A colossal cataclysmic explosion in the night sky over an ancient metropolis. An immense apocalyptic fiery crimson "
                "sphere expands outward with blinding shockwaves, shattering clouds and vaporizing rooftops in intense fiery red glow. "
                "Blinding orange and blood-red radiant light engulfs the entire frame with burning flying embers, photorealistic 8k, "
                "epic cinematic disaster, 16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: The defiant cultivator laughs maniacally, his hands rapidly forming ancient occult hand seals as a fierce crimson "
                "magical flame ignites violently within his chest. "
                "3-6s: The opposing cultivator recoils in alarmed horror as the crimson flame erupts outward, swelling into a colossal "
                "apocalyptic fireball that fractures the heavens with deafening shockwaves. "
                "6-8s: Blinding blood-red shockwaves expand outward, tearing apart ancient roof tiles and wooden structures below, "
                "engulfing the camera lens into a blazing fiery crimson whiteout."
            ),
        },
        # Cảnh 5 (00:32 - 00:40)
        {
            "index": 5,
            "title": "Tỉnh Lại Giữa Biển Tro Tàn",
            "start_tag": "frame_05_bloody_hand_in_ashes",
            "end_tag": "frame_06_old_man_sitting_in_smoking_ruins",
            "start_prompt": (
                "A low-angle close-up of a trembling, blood-stained elderly hand reaching out from charred ash and smoldering blackened rubble. "
                "Silent dark night, rising smoke, glowing embers among broken bricks and scorched timber. Photorealistic 8k, gritty realistic "
                "texture, shallow depth of field, 16:9 aspect ratio."
            ),
            "end_prompt": (
                "A cinematic medium shot of the bruised and bloodied 70-year-old elder statesman weakly sitting up against broken stone masonry "
                "amidst smoking ruins. His crimson robes are torn and covered in grey soot, coughing painfully with blood on his lips, staring "
                "with dazed shock at the flattened graveyard of his grand palace under the dark misty sky. Photorealistic 8k, somber desolation, "
                "16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: Amidst silent smoldering rubble under the eerie night sky, the elderly man's trembling blood-stained hand slowly stirs "
                "amongst charred debris and rising smoke. "
                "3-6s: He coughs painfully, spewing blood onto the ashes, feebly pushing his fragile aging body upright from the scorched earth "
                "amidst the smell of burnt ruins. "
                "6-8s: Shaking off dust, he weakly sits up against shattered stone blocks, staring blankly in dazed disbelief at the silent "
                "devastating graveyard that once was his grand hall."
            ),
        },
        # Cảnh 6 (00:40 - 00:48)
        {
            "index": 6,
            "title": "Nụ Cười Chua Xót Bên Góc Tường Đổ",
            "start_tag": "frame_06_old_man_sitting_in_smoking_ruins",  # NỐI CHUỖI TỪ END CẢNH 5
            "end_tag": "frame_07_aged_statesman_slumped_wall_smiling",
            "start_prompt": None,
            "end_prompt": (
                "A cinematic medium close-up of the aged statesman slumped wearily against a crumbling brick wall corner in the ruined city. "
                "Under the cold moonlight, his weathered face carries a bitter, melancholic, self-mocking smile as he gazes up at the indifferent "
                "dark sky, realizing fifty years of worldly imperial power were utterly crushed in a single second. Cinematic lighting, photorealistic "
                "8k, deep emotional sorrow, 16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: The exhausted statesman drags his frail body through the ruined gateway, revealing the imperial city transformed into a "
                "smoking wasteland of fire and collapsed buildings. "
                "3-6s: Deprived of hearing from the blast, he stumbles weakly toward a broken brick wall corner, sliding down into a seated collapse "
                "against the cold cracked masonry. "
                "6-8s: Gazing upward into the indifferent dark heavens, a bitter self-mocking laugh slowly breaks across his weathered wrinkled "
                "face, settling into motionless melancholy contemplation."
            ),
        },
        # Cảnh 7 (00:48 - 00:56)
        {
            "index": 7,
            "title": "Dị Bảo Thức Tỉnh: Thật Là Giả Thì Giả Cũng Là Thật",
            "start_tag": "frame_07_aged_statesman_slumped_wall_smiling",  # NỐI CHUỖI TỪ END CẢNH 6
            "end_tag": "frame_08_eight_golden_characters_water_void",
            "start_prompt": None,
            "end_prompt": (
                "A mystical cinematic shot of reality dissolving into a dark aquatic void with rippling water rings. Eight gigantic ancient "
                "golden Chinese calligraphy characters float weightlessly in mid-air emitting divine sacred radiance: '真亦是假假亦是真'. "
                "Shimmering cyan and gold holographic light particles hover gracefully in the mystical darkness. Photorealistic 8k, ethereal "
                "spiritual aesthetic, 16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: Seated in the dark ruins, the old man closes his eyes in intense concentration. The desolate physical world begins to blur "
                "and ripple like an undulating watery mirage. "
                "3-6s: Reality dissolves into a mystical dark aquatic void. Eight colossal golden calligraphy characters illuminate out of the "
                "darkness with sacred ethereal radiance. "
                "6-8s: The golden ancient glyphs pulse softly before dissipating into a shimmering translucent holographic light barrier hovering "
                "gracefully around his consciousness."
            ),
        },
        # Cảnh 8 (00:56 - 01:04)
        {
            "index": 8,
            "title": "Đèn Kéo Quân 50 Năm Vỡ Vụn Thành Sao Băng",
            "start_tag": "frame_08_eight_golden_characters_water_void",  # NỐI CHUỖI TỪ END CẢNH 7
            "end_tag": "frame_09_temporal_vortex_shattering_stars",
            "start_prompt": None,
            "end_prompt": (
                "An infinite cosmic time vortex tunnel spiraling backwards through dimensions. Millions of brilliant golden and silver star "
                "fragments and crystal memory shards rush backward through a dark chronal wormhole. Luminous stardust trails, cosmic hyperspace "
                "phenomenon, photorealistic 8k, breathtaking temporal depth, 16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: Across the radiant mystical screen, countless vivid cinematic vignettes depicting fifty years of political triumph, "
                "battles, and wealth rotate swiftly like a revolving lantern. "
                "3-6s: Two lines of glowing script appear asking to reset. He mentally confirms, causing the entire tapestry of worldly memories "
                "to shatter like brittle crystal into brilliant stars. "
                "6-8s: Millions of luminous star fragments stream backward into a swirling chronal vortex, accelerating through an infinite spiral "
                "tunnel toward the origin point."
            ),
        },
        # Cảnh 9 (01:04 - 01:12)
        {
            "index": 9,
            "title": "Tỉnh Dậy Trong Thư Phòng Thuở Hàn Vi",
            "start_tag": "frame_09_young_scholar_hands_rustic_desk",
            "end_tag": "frame_10_young_scholar_sitting_cyan_metrics",
            "start_prompt": (
                "A cinematic close-up of smooth, youthful 20-year-old male hands resting on a rustic unvarnished wooden study desk. Beside the "
                "hands are a stone inkwell with Chinese calligraphy brush and handwritten ancient books. Soft morning dust motes drifting in "
                "gentle warm window light. Photorealistic 8k, peaceful simplicity, shallow depth of field, 16:9 aspect ratio."
            ),
            "end_prompt": (
                "A cinematic medium shot of a handsome 20-year-old scholar in simple modest grey linen Hanfu robes, sitting upright in his small "
                "humble wooden study. His youthful face contrasts strikingly with deep, profound, ancient eyes carrying 166 years of worldly "
                "experience. In front of him float delicate translucent cyan holographic glyphs showing age numbers: 20 and 166. Photorealistic 8k, "
                "contemplative tranquil atmosphere, 16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: The young scholar's smooth youthful hands rest on a rustic wooden study desk beside an inkstone and old paper manuscripts. "
                "His fingers twitch as life surges back into his body. "
                "3-6s: He opens his sharp eyes, looking around the modest rustic study room in shock, realizing his 20-year-old mortal body has "
                "returned while retaining 166 years of worldly wisdom. "
                "6-8s: Floating translucent cyan numerical glyphs materialize before him showing his age metrics, as he sits upright with calm "
                "unwavering composure."
            ),
        },
        # Cảnh 10 (01:12 - 01:20)
        {
            "index": 10,
            "title": "Lời Thề Bắt Tiên Dưới Bình Minh",
            "start_tag": "frame_10_young_scholar_sitting_cyan_metrics",  # NỐI CHUỖI TỪ END CẢNH 9
            "end_tag": "frame_11_young_scholar_window_sunrise_fist",
            "start_prompt": None,
            "end_prompt": (
                "A heroic cinematic side-profile medium close-up of the 20-year-old scholar standing before an open wooden lattice window at dawn. "
                "Golden morning sunlight bathes his sharp, resolute jawline and intense determined eyes. His right hand is tightly clenched into "
                "a fist against his chest. Outside, distant mist-shrouded mountain peaks glow in the golden sunrise. Photorealistic 8k, inspiring "
                "epic dawn lighting, 16:9 aspect ratio."
            ),
            "video_prompt": (
                "0-3s: The young scholar turns away from the desk, striding purposefully toward the open lattice paper window where golden morning "
                "dawn begins to break. "
                "3-6s: Warm sunlight bathes his determined profile. Camera glides around to capture his sharp, resolute expression as he gazes at "
                "the distant mountains under the sunrise. "
                "6-8s: He clenches his right fist tightly with unshakeable resolve, a fearless visionary smile appearing on his lips as the camera "
                "holds firmly on his heroic stance."
            ),
        },
    ]

    connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        if not await check_health(session):
            sys.exit(1)


        # ======================================================================
        # VÒNG 1: DISPATCH TOÀN BỘ CẢNH (SINH ẢNH, KHỬ LOGO, SUBMIT VIDEO LÊN FLOW)
        # ======================================================================
        logger.info("\n" + "=" * 70)
        logger.info("👉 VÒNG 1: TIẾN HÀNH CHUẨN BỊ ẢNH VÀ GỬI LỆNH TẠO VIDEO TOÀN BỘ CẢNH")
        logger.info("=" * 70)

        for sc in scenes_spec:
            idx = sc["index"]
            title = sc["title"]
            clip_file = dirs["clips"] / f"scene_{idx:02d}_8s.mp4"
            if clip_file.exists() and clip_file.stat().st_size > 100000:
                completed_clips[idx] = str(clip_file.resolve())
                completed_clips[str(idx)] = str(clip_file.resolve())
                logger.info(f"✅ Phân cảnh #{idx:02d} ĐÃ HOÀN TẤT từ trước: {clip_file.name}")
                continue

            pending_ops = manifest.get("pending_ops", {})
            if str(idx) in pending_ops or idx in pending_ops:
                op_existing = pending_ops.get(str(idx)) or pending_ops.get(idx)
                logger.info(f"⏳ Phân cảnh #{idx:02d} ĐÃ SUBMIT từ trước (Op ID: {op_existing}), chuyển sang cảnh tiếp theo...")
                continue

            logger.info("\n" + "-" * 60)
            logger.info(f"🚀 BẮT ĐẦU CHUẨN BỊ & GỬI API CẢNH #{idx:02d}: {title.upper()}")
            logger.info("-" * 60)

            # 1. Chuẩn bị Start Frame
            start_mid = None
            if sc["start_tag"] in media_cache:
                start_mid = media_cache[sc["start_tag"]]
                logger.info(f"  [START FRAME NỐI TIẾP] Tái sử dụng '{sc['start_tag']}': {start_mid}")
            else:
                start_mid = await generate_and_clean_image(
                    session=session,
                    project_id=PROJECT_ID,
                    tag=sc["start_tag"],
                    prompt=sc["start_prompt"],
                    dirs=dirs,
                    cache_dict=media_cache,
                )

            # 2. Chuẩn bị End Frame
            end_mid = None
            if sc["end_tag"] in media_cache:
                end_mid = media_cache[sc["end_tag"]]
                logger.info(f"  [END FRAME ĐÃ CÓ] Tái sử dụng '{sc['end_tag']}': {end_mid}")
            else:
                end_mid = await generate_and_clean_image(
                    session=session,
                    project_id=PROJECT_ID,
                    tag=sc["end_tag"],
                    prompt=sc["end_prompt"],
                    dirs=dirs,
                    cache_dict=media_cache,
                )

            # 3. Kích hoạt sinh video F2F 8s
            logger.info(f"  [SUBMIT VEO 3.1 F2F] Cảnh #{idx:02d} (Start: {start_mid} -> End: {end_mid})")
            video_payload = {
                "start_image_media_id": start_mid,
                "end_image_media_id": end_mid,
                "prompt": sc["video_prompt"],
                "project_id": PROJECT_ID,
                "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
                "duration": 8,
                "duration_s": 8,
                "user_paygate_tier": "PAYGATE_TIER_TWO",
                "count": 1,
                "title": f"{MOVIE_SLUG}_scene_{idx:02d}_8s",
                "display_name": f"{MOVIE_SLUG}_scene_{idx:02d}_8s",
            }

            v_url = f"{API_BASE}/api/flow/generate-video"
            async with session.post(v_url, json=video_payload, timeout=120) as v_resp:
                v_data = await v_resp.json()
                if v_resp.status != 200:
                    raise RuntimeError(f"Lỗi submit video Cảnh #{idx}: {v_data}")

            op_id = extract_op_id(v_data)
            logger.info(f"  🎉 SUBMIT THÀNH CÔNG CẢNH #{idx:02d}! Op ID: {op_id}")
            pending_ops[str(idx)] = op_id
            manifest["pending_ops"] = pending_ops
            manifest["media_cache"] = media_cache
            manifest["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            dirs["manifest"].write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

            # Nghỉ 5 giây giữa các request để tuân thủ cooldown an toàn
            await asyncio.sleep(5)

        # ======================================================================
        # VÒNG 2: CONTINUOUS POLLING & DOWNLOAD CHO TOÀN BỘ CÁC CẢNH
        # ======================================================================
        logger.info("\n" + "=" * 70)
        logger.info("👉 VÒNG 2: THEO DÕI TRẠNG THÁI VÀ TẢI VỀ CÁC CLIP VIDEO")
        logger.info("=" * 70)

        poll_url = f"{API_BASE}/api/flow/check-status"
        start_poll_all = time.time()
        max_poll_time = 3600  # 60 phút tối đa

        while time.time() - start_poll_all < max_poll_time:
            pending_ops = manifest.get("pending_ops", {})
            remaining = [idx for idx in range(1, 11) if str(idx) not in completed_clips and idx not in completed_clips]

            if not remaining:
                logger.info("🎉 TẤT CẢ 10 PHÂN CẢNH ĐÃ HOÀN TẤT VÀ TẢI VỀ ĐẦY ĐỦ!")
                break

            for idx in remaining:
                op_id = pending_ops.get(str(idx)) or pending_ops.get(idx)
                if not op_id:
                    continue

                clip_file = dirs["clips"] / f"scene_{idx:02d}_8s.mp4"
                check_payload = {
                    "operations": [{"operation": {"name": op_id}}],
                    "project_id": PROJECT_ID,
                }
                try:
                    async with session.post(poll_url, json=check_payload, timeout=30) as p_resp:
                        if p_resp.status != 200:
                            continue
                        p_res = await p_resp.json()
                        ops = p_res.get("operations", [])
                        if not ops:
                            continue
                        entry = ops[0]
                        st = entry.get("status")
                        logger.info(f"  [Cảnh {idx:02d} Polling] Status: {st}")

                        if st == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                            meta_v = entry.get("operation", {}).get("metadata", {}).get("video", {})
                            v_url = meta_v.get("fifeUrl") or meta_v.get("url")
                            if v_url:
                                async with session.get(v_url, timeout=120) as dl:
                                    if dl.status == 200:
                                        vb = await dl.read()
                                        clip_file.write_bytes(vb)
                                        logger.info(f"  🎉 TẢI THÀNH CÔNG CLIP #{idx:02d}: {clip_file.name} ({len(vb)/(1024*1024):.2f} MB)")
                                        completed_clips[idx] = str(clip_file.resolve())
                                        completed_clips[str(idx)] = str(clip_file.resolve())
                                        extract_motion_frames(clip_file, dirs["frames"], idx, [0.0, 4.0, 8.0])

                                        manifest["completed_clips"] = completed_clips
                                        manifest["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
                                        dirs["manifest"].write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
                        elif st in ("MEDIA_GENERATION_STATUS_FAILED", "MEDIA_GENERATION_STATUS_REJECTED"):
                            logger.error(f"  ❌ Cảnh #{idx:02d} thất bại: {entry.get('error')}")
                except Exception as ex:
                    logger.warning(f"  Cảnh #{idx:02d} polling exception: {ex}")

            await asyncio.sleep(12)


        # 5. Ghép toàn bộ clip lại thành master video 80s
        all_clip_files = [dirs["clips"] / f"scene_{i:02d}_8s.mp4" for i in range(1, 11)]
        existing_clips = [p for p in all_clip_files if p.exists()]
        master_output = dirs["clips"] / "dai_huyen_thai_su_master_80s.mp4"
        concat_all_scenes_opencv(existing_clips, master_output)

        logger.info("\n" + "=" * 80)
        logger.info("🏁 TOÀN BỘ 10 PHÂN CẢNH MASTER ĐÃ KẾT XUẤT VÀ GHÉP NỐI THÀNH CÔNG!")
        logger.info("  Master Video: %s", master_output)
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

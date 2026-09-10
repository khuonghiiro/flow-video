"""Pipeline Frame-to-Frame (F2F) Video 8s với Hệ Thống Khử Logo & Tracking Thứ Tự Tuyệt Đối.

Cốt truyện: Thái Sư Huyền Kinh Lý Phàm - Luân Hồi Bắt Tiên.
Quy trình:
1. Sinh các khung hình song song qua Flow API (/api/flow/generate-image).
2. Tải ảnh thô về thư mục agent-veo3/output/movies/<slug>/watermarks/.
3. Khử sạch watermark bằng Reverse Alpha Blending sang .../cleaned/.
4. Upload song song các ảnh sạch lên Google Flow (/api/flow/upload-image).
5. Ghi nhận bảng đối chiếu (Frame Manifest) quản lý thứ tự chính xác:
   Index -> Role (START/END) -> Raw Path -> Clean Path -> Uploaded Media UUID.
6. Kích hoạt sinh Video 8s Frame-to-Frame (Veo 3.1 Interpolation nprQif).
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

# Cấu hình UTF-8 cho Windows Console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thêm đường dẫn scripts để import module remove_gemini_watermark
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from remove_gemini_watermark import remove_watermark

# Thiết lập logging chuẩn
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("f2f_pipeline")

API_BASE = "http://127.0.0.1:8100"
DEFAULT_PROJECT_ID = "bd376b57-e9a5-46f3-9f56-101e2967697c"
MOVIE_SLUG = "ly_pham_bat_tien"


def setup_directories(slug: str) -> Dict[str, Path]:
    """Khởi tạo và trả về cây thư mục làm việc chuẩn cho dự án."""
    base_dir = SCRIPT_DIR.parent / "output" / "movies" / slug
    raw_dir = base_dir / "watermarks"
    cleaned_dir = base_dir / "cleaned"
    clips_dir = base_dir / "clips"

    for d in (base_dir, raw_dir, cleaned_dir, clips_dir):
        d.mkdir(parents=True, exist_ok=True)

    return {
        "base": base_dir,
        "raw": raw_dir,
        "cleaned": cleaned_dir,
        "clips": clips_dir,
        "manifest": base_dir / "frame_manifest.json",
    }


async def check_health(session: aiohttp.ClientSession) -> bool:
    """Kiểm tra trạng thái Backend và kết nối Chrome Extension."""
    url = f"{API_BASE}/health"
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                ext_ok = data.get("extension_connected", False)
                if not ext_ok:
                    logger.error("Chrome Extension CHƯA KẾT NỐI! Vui lòng mở flow.google.com trên Chrome.")
                    return False
                logger.info("Pre-flight Health Check OK (Extension Connected: True)")
                return True
    except Exception as e:
        logger.error("Không thể kết nối đến Backend: %s", e)
    return False


async def generate_single_image(
    session: aiohttp.ClientSession,
    project_id: str,
    frame_spec: Dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Gửi yêu cầu sinh 1 ảnh qua Google Flow API."""
    async with semaphore:
        idx = frame_spec["index"]
        tag = frame_spec["tag"]
        prompt = frame_spec["prompt"]
        aspect = frame_spec.get("aspect_ratio", "IMAGE_ASPECT_RATIO_LANDSCAPE")

        logger.info("[SINH ẢNH] Frame #%02d [%s] bắt đầu gửi tới Flow...", idx, tag)
        url = f"{API_BASE}/api/flow/generate-image"
        payload = {
            "prompt": prompt,
            "project_id": project_id,
            "aspect_ratio": aspect,
            "user_paygate_tier": "PAYGATE_TIER_TWO",
            "title": f"{MOVIE_SLUG}_frame_{idx:02d}_{tag}",
        }

        t0 = time.time()
        async with session.post(url, json=payload, timeout=240) as resp:
            data = await resp.json()
            elapsed = time.time() - t0

            if resp.status != 200:
                logger.error("Frame #%02d thất bại (HTTP %d): %s", idx, resp.status, data)
                raise RuntimeError(f"Lỗi sinh ảnh Frame #{idx}: {data}")

            # Trích xuất media_id và download URL
            media_list = data.get("media", [])
            if not media_list and isinstance(data.get("data"), dict):
                media_list = data["data"].get("media", [])

            url_found = None
            orig_media_id = None

            if media_list and isinstance(media_list, list):
                item = media_list[0]
                orig_media_id = item.get("name")
                img_block = item.get("image", {})
                gen_img = img_block.get("generatedImage", {}) if isinstance(img_block, dict) else {}
                url_found = gen_img.get("fifeUrl") or img_block.get("fifeUrl") or item.get("fifeUrl")

            if not url_found:
                raise RuntimeError(f"Không tìm thấy URL tải ảnh cho Frame #{idx}: {data}")

            logger.info("Frame #%02d [%s] sinh xong sau %.1fs | Media ID: %s", idx, tag, elapsed, orig_media_id)
            return {
                "index": idx,
                "tag": tag,
                "role": frame_spec["role"],
                "prompt": prompt,
                "original_flow_media_id": orig_media_id,
                "download_url": url_found,
            }


async def download_image_file(
    session: aiohttp.ClientSession,
    url: str,
    dest_path: Path,
) -> bool:
    """Tải file ảnh từ URL về lưu trữ cục bộ."""
    async with session.get(url, timeout=60) as resp:
        if resp.status == 200:
            content = await resp.read()
            dest_path.write_bytes(content)
            logger.info("Đã tải về: %s (%.1f KB)", dest_path.name, len(content) / 1024.0)
            return True
        logger.error("Tải ảnh thất bại HTTP %d: %s", resp.status, url[:80])
        return False


def clean_single_watermark(raw_path: Path, clean_path: Path) -> float:
    """Khử logo watermark bằng Reverse Alpha Blending chuẩn xác, giữ nguyên 100% chi tiết pixel, không làm mờ."""
    img = cv2.imread(str(raw_path))
    if img is None:
        raise RuntimeError(f"Không thể đọc file ảnh: {raw_path}")

    t0 = time.time()
    cleaned = remove_watermark(img, aggressive=False)
    cv2.imwrite(str(clean_path), cleaned, [int(cv2.IMWRITE_PNG_COMPRESSION), 3])
    return (time.time() - t0) * 1000.0


async def upload_clean_image_task(
    session: aiohttp.ClientSession,
    project_id: str,
    frame_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Upload ảnh sạch lên Google Flow và lưu lại UUID trả về."""
    clean_path = Path(frame_info["clean_local_path"])
    idx = frame_info["index"]
    tag = frame_info["tag"]

    logger.info("[UPLOAD SẠCH] Đang upload Frame #%02d [%s] lên Flow...", idx, tag)
    url = f"{API_BASE}/api/flow/upload-image"
    payload = {
        "file_path": str(clean_path.resolve()),
        "project_id": project_id,
        "file_name": clean_path.name,
    }

    async with session.post(url, json=payload, timeout=60) as resp:
        data = await resp.json()
        new_uuid = data.get("media_id") or data.get("mediaId")
        if not new_uuid and isinstance(data.get("raw"), dict):
            raw = data["raw"]
            new_uuid = raw.get("name") or raw.get("id") or raw.get("_mediaId")
            if not new_uuid and isinstance(raw.get("media"), dict):
                new_uuid = raw["media"].get("name") or raw["media"].get("id")

        if not new_uuid:
            raise RuntimeError(f"Upload Frame #{idx} không nhận được UUID: {data}")

        logger.info("Frame #%02d [%s] UPLOAD THÀNH CÔNG! Media UUID Mới: %s", idx, tag, new_uuid)
        frame_info["uploaded_clean_media_id"] = new_uuid
        return frame_info


async def trigger_f2f_video_8s(
    session: aiohttp.ClientSession,
    project_id: str,
    start_mid: str,
    end_mid: str,
    video_prompt: str,
    title: str,
) -> Dict[str, Any]:
    """Kích hoạt sinh video 8s Frame-to-Frame qua Veo 3.1 Interpolation RPC nprQif."""
    logger.info("=" * 70)
    logger.info("[VEO 3.1 F2F] ĐANG GỬI YÊU CẦU TẠO VIDEO 8S FRAME-TO-FRAME")
    logger.info("  Start Frame UUID: %s", start_mid)
    logger.info("  End Frame UUID:   %s", end_mid)
    logger.info("  Duration:         8.0 giây (veo_3_1_interpolation_lite_low_priority)")
    logger.info("  Prompt hành động: %s", video_prompt)
    logger.info("=" * 70)

    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": start_mid,
        "end_image_media_id": end_mid,
        "prompt": video_prompt,
        "project_id": project_id,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "duration": 8,
        "duration_s": 8,
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "count": 1,
        "title": title,
        "display_name": title,
    }

    t0 = time.time()
    async with session.post(url, json=payload, timeout=120) as resp:
        data = await resp.json()
        elapsed = time.time() - t0

        if resp.status != 200:
            logger.error("Lỗi gửi yêu cầu sinh video (HTTP %d): %s", resp.status, data)
            raise RuntimeError(f"Lỗi tạo video 8s: {data}")

        logger.info("Video F2F 8s submit thành công sau %.1fs!", elapsed)
        return data


def save_manifest(manifest_path: Path, manifest: Dict[str, Any]):
    """Ghi dữ liệu manifest xuống đĩa JSON với định dạng UTF-8 rõ ràng."""
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Đã lưu bảng đối chiếu Frame Manifest: %s", manifest_path)


async def execute_f2f_pipeline(
    project_id: str = DEFAULT_PROJECT_ID,
    slug: str = MOVIE_SLUG,
):
    """Thực thi toàn bộ luồng quy trình khép kín."""
    dirs = setup_directories(slug)
    logger.info("Khởi động Pipeline F2F cho dự án: %s (PID: %s)", slug, project_id)

    # 1. Định nghĩa kịch bản các khung hình theo cốt truyện Thái sư Lý Phàm
    frame_definitions = [
        {
            "index": 1,
            "tag": "ly_pham_mung_tho_dai_dien",
            "role": "START_FRAME",
            "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "prompt": (
                "Cinematic wide establishing shot of Grand Chancellor Ly Pham 70th birthday lavish banquet "
                "inside imperial Chancellor Palace hall of Da Xuan kingdom. Over 70-year-old Ly Pham with silver grey hair "
                "and neat beard, wearing luxurious dark crimson and gold silk Hanfu robes, sitting proudly on elevated ornate wooden throne, "
                "holding a carved white jade wine cup with a subtle satisfied smile. Civil and military officials in formal court robes "
                "kneeling and raising toast across the magnificent hall illuminated by hundreds of golden warm hanging lanterns and tall candles, "
                "ancient Chinese court architecture, intricate wooden carvings, cinematic lighting, photorealistic 8k, highly detailed, depth of field."
            )
        },
        {
            "index": 2,
            "tag": "tien_nhan_ha_pham_huyen_kinh",
            "role": "END_FRAME",
            "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "prompt": (
                "Cinematic exterior medium-wide shot looking up from the balcony terrace of Chancellor Palace into the dark night sky "
                "over Xuan Jing city. Two brilliant silver comet-like light streaks blazing through the night clouds, coming to an abrupt stop "
                "floating high in midair. Two immortal daoist cultivators hovering weightlessly above the ancient tiled rooftops of the capital city, "
                "surrounded by swirling celestial wind and crackling silver lightning arcs, glaring confrontation in midair. "
                "Below, ancient city rooftops, night mist, dramatic cinematic contrast, celestial glowing aura, photorealistic 8k, hyper-detailed."
            )
        }
    ]

    video_prompt_8s = (
        "0-3s: Interior lavish banquet hall, Ly Pham slowly raises his jade wine cup and smiles proudly amidst cheering kneeling officials. "
        "3-6s: A sudden earth-shaking tremor rumbles, candle flames flicker violently, Ly Pham puts down his cup with an alarmed frown, "
        "striding quickly toward the open balcony terrace. "
        "6-8s: Dynamic cinematic camera pan from behind Ly Pham tilting upward into the night sky, revealing two blinding silver comet streaks "
        "halting above Xuan Jing city as two immortal cultivators hover in midair with overwhelming celestial aura."
    )

    async with aiohttp.ClientSession() as session:
        # Bước 1: Kiểm tra kết nối
        if not await check_health(session):
            sys.exit(1)

        # Bước 2: Sinh ảnh song song
        logger.info("\n=== BƯỚC 1/5: SINH CÁC KHUNG HÌNH SONG SONG QUA FLOW API ===")
        semaphore = asyncio.Semaphore(2)  # 2 request song song an toàn
        gen_tasks = [
            generate_single_image(session, project_id, f, semaphore)
            for f in frame_definitions
        ]
        generated_results = await asyncio.gather(*gen_tasks)

        # Bước 3: Tải ảnh thô về và khử logo
        logger.info("\n=== BƯỚC 2/5: TẢI ẢNH THÔ VỀ & KHỬ LOGO REVERSE ALPHA BLENDING ===")
        processed_frames = []
        for res in generated_results:
            idx = res["index"]
            tag = res["tag"]
            raw_path = dirs["raw"] / f"frame_{idx:02d}_{tag}_raw.png"
            clean_path = dirs["cleaned"] / f"frame_{idx:02d}_{tag}_clean.png"

            # Tải ảnh
            await download_image_file(session, res["download_url"], raw_path)

            # Khử logo
            t_ms = clean_single_watermark(raw_path, clean_path)
            logger.info("Khử sạch logo Frame #%02d [%s] trong %.1fms -> %s", idx, tag, t_ms, clean_path.name)

            frame_entry = {
                "index": idx,
                "tag": tag,
                "role": res["role"],
                "prompt": res["prompt"],
                "original_flow_media_id": res["original_flow_media_id"],
                "raw_local_path": str(raw_path.resolve()),
                "clean_local_path": str(clean_path.resolve()),
                "uploaded_clean_media_id": None,
            }
            processed_frames.append(frame_entry)

        # Bước 4: Upload song song các ảnh sạch lên Google Flow
        logger.info("\n=== BƯỚC 3/5: UPLOAD SONG SONG ẢNH ĐÃ KHỬ LOGO LÊN FLOW ===")
        # Đảm bảo danh sách được sắp xếp theo đúng index
        processed_frames.sort(key=lambda x: x["index"])

        upload_tasks = [
            upload_clean_image_task(session, project_id, f)
            for f in processed_frames
        ]
        uploaded_frames = await asyncio.gather(*upload_tasks)

        # Bước 5: Cập nhật Frame Manifest với bảng đối chiếu chính xác tuyệt đối
        manifest_data = {
            "project_id": project_id,
            "movie_slug": slug,
            "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "video_aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "frames": uploaded_frames,
            "videos": [
                {
                    "clip_index": 1,
                    "duration_s": 8,
                    "start_frame_index": 1,
                    "end_frame_index": 2,
                    "start_clean_media_id": uploaded_frames[0]["uploaded_clean_media_id"],
                    "end_clean_media_id": uploaded_frames[1]["uploaded_clean_media_id"],
                    "video_prompt": video_prompt_8s,
                    "status": "SUBMITTED",
                    "operation_result": None,
                }
            ]
        }
        save_manifest(dirs["manifest"], manifest_data)

        # In bảng tra cứu đối chiếu trực quan
        print("\n" + "=" * 90)
        print("  BẢNG ĐỐI CHIẾU THỨ TỰ KHUNG HÌNH (FRAME MANIFEST TRACKING TABLE)")
        print("=" * 90)
        print(f" {'STT':<4} | {'VAI TRÒ':<12} | {'TÊN KHUNG HÌNH':<30} | {'CLEAN MEDIA UUID (ĐÃ UPLOAD)':<36}")
        print("-" * 90)
        for f in uploaded_frames:
            print(f" #{f['index']:<3} | {f['role']:<12} | {f['tag']:<30} | {f['uploaded_clean_media_id']:<36}")
        print("=" * 90 + "\n")

        # Bước 6: Kích hoạt tạo Video 8s Frame-to-Frame
        logger.info("\n=== BƯỚC 4/5: TẠO VIDEO 8S FRAME-TO-FRAME (Veo 3.1 Interpolation) ===")
        start_clean_id = uploaded_frames[0]["uploaded_clean_media_id"]
        end_clean_id = uploaded_frames[1]["uploaded_clean_media_id"]
        video_title = f"{slug}_scene_01_f2f_8s"

        video_res = await trigger_f2f_video_8s(
            session=session,
            project_id=project_id,
            start_mid=start_clean_id,
            end_mid=end_clean_id,
            video_prompt=video_prompt_8s,
            title=video_title,
        )

        manifest_data["videos"][0]["operation_result"] = video_res
        save_manifest(dirs["manifest"], manifest_data)

        print("\n" + "=" * 90)
        print("  HOÀN TẤT TOÀN BỘ QUY TRÌNH TẠO VIDEO 8S FRAME-TO-FRAME THÀNH CÔNG!")
        print(f"  - Project ID:         {project_id}")
        print(f"  - Start Frame (Sạch): {uploaded_frames[0]['clean_local_path']} -> UUID: {start_clean_id}")
        print(f"  - End Frame (Sạch):   {uploaded_frames[1]['clean_local_path']} -> UUID: {end_clean_id}")
        print(f"  - Video Duration:     8.0s (Veo 3.1 Interpolation)")
        print(f"  - File Manifest:      {dirs['manifest']}")
        print("=" * 90 + "\n")


if __name__ == "__main__":
    asyncio.run(execute_f2f_pipeline())

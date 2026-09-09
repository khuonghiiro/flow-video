"""Pipeline thực thi Phân cảnh 1 (00:00 - 00:08): Đại Tiệc Mừng Thọ 70 Tuổi.
Dự án: Đại Huyền Thái Sư - Hoàn Chân Bắt Tiên (PID: 08f70524-3b10-49d0-9b68-0b2fde61190e).
Quy trình khép kín:
1. Sinh Start Frame (toàn cảnh sảnh tiệc) & End Frame (cận cảnh Lý Phàm uống rượu vuốt râu).
2. Tải ảnh thô về và khử watermark bằng Reverse Alpha Blending.
3. Upload 2 ảnh sạch lên Google Flow lấy Media UUID mới.
4. Gửi yêu cầu sinh Video 8s Frame-to-Frame (Veo 3.1 Interpolation).
5. Polling kiểm tra trạng thái và tự động tải video MP4 về khi hoàn thành.
6. Trích xuất các khung hình mẫu (0s, 2s, 4s, 6s, 8s) để kiểm định độ mượt.
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
logger = logging.getLogger("scene01_pipeline")

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
    async with session.get(url, timeout=60) as resp:
        if resp.status == 200:
            content = await resp.read()
            dest_path.write_bytes(content)
            logger.info("Đã tải về: %s (%.1f KB)", dest_path.name, len(content) / 1024.0)
            return True
        logger.error("Tải ảnh thất bại HTTP %d: %s", resp.status, url[:80])
        return False


def clean_single_watermark(raw_path: Path, clean_path: Path) -> float:
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

        logger.info("Frame #%02d [%s] UPLOAD THÀNH CÔNG! Media UUID: %s", idx, tag, new_uuid)
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
    logger.info("=" * 70)
    logger.info("[VEO 3.1 F2F] GỬI YÊU CẦU TẠO VIDEO 8S FRAME-TO-FRAME")
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

        logger.info("Video F2F 8s submit thành công sau %.1fs! Response: %s", elapsed, str(data)[:200])
        return data


def extract_op_id_from_response(video_res: Dict[str, Any]) -> str:
    """Trích xuất ID operation từ phản hồi nprQif của Google Flow một cách toàn diện."""
    if not isinstance(video_res, dict):
        return ""

    # 1. Trực tiếp từ operations list
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

    # 2. Tìm đệ quy bất kỳ key "name" có định dạng UUID hoặc operations/
    def find_op_name(obj):
        if isinstance(obj, dict):
            if "name" in obj and isinstance(obj["name"], str):
                val = obj["name"]
                if len(val) == 36 and val.count("-") == 4:
                    return val
                if "operations/" in val:
                    return val
            for v in obj.values():
                res = find_op_name(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_op_name(item)
                if res:
                    return res
        return None

    found = find_op_name(video_res)
    return found or video_res.get("operationId") or video_res.get("id") or ""



async def poll_video_until_ready(
    session: aiohttp.ClientSession,
    project_id: str,
    operation_id: str,
    max_wait_seconds: int = 480,
    poll_interval: int = 10,
) -> Dict[str, Any]:
    """Polling kiểm tra tiến độ sinh video qua /api/flow/check-status."""
    logger.info("[POLLING] Bắt đầu theo dõi tiến độ Video Op: %s...", operation_id)
    url = f"{API_BASE}/api/flow/check-status"
    payload = {
        "operations": [{"operation": {"name": operation_id}}],
        "project_id": project_id,
    }

    start_time = time.time()
    attempt = 0

    while time.time() - start_time < max_wait_seconds:
        attempt += 1
        await asyncio.sleep(poll_interval)

        try:
            async with session.post(url, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    logger.warning("  [%02d] Polling HTTP %d", attempt, resp.status)
                    continue

                res = await resp.json()
                ops = res.get("operations", [])
                if not ops:
                    logger.info("  [%02d] (+%.0fs) Chưa có record operation, đang chờ Flow...", attempt, time.time() - start_time)
                    continue

                entry = ops[0]
                status = entry.get("status")
                elapsed = time.time() - start_time
                logger.info("  [%02d] (+%.0fs) Status: %s", attempt, elapsed, status)

                if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                    meta_video = entry.get("operation", {}).get("metadata", {}).get("video", {})
                    video_url = meta_video.get("fifeUrl") or meta_video.get("url")
                    media_id = meta_video.get("mediaId") or operation_id
                    logger.info("[THÀNH CÔNG] Video đã sẵn sàng! Media ID: %s | URL: %s", media_id, video_url)
                    return {
                        "status": "SUCCESSFUL",
                        "media_id": media_id,
                        "video_url": video_url,
                        "elapsed_s": elapsed,
                    }
                elif status in ("MEDIA_GENERATION_STATUS_FAILED", "MEDIA_GENERATION_STATUS_REJECTED"):
                    logger.error("[THẤT BÀI] Quá trình sinh video bị lỗi: %s", entry)
                    return {
                        "status": status,
                        "error": entry.get("error") or "Generation rejected",
                    }
        except Exception as e:
            logger.warning("  [%02d] Lỗi mạng khi polling: %s", attempt, e)

    raise TimeoutError(f"Hết thời gian chờ ({max_wait_seconds}s) cho video {operation_id}")


def extract_motion_frames(video_path: Path, output_dir: Path, timestamps: List[float]):
    """Trích xuất các khung hình mẫu tại các mốc thời gian để kiểm tra chuyển động."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    logger.info("Video specs: %.2f FPS, %d frames, %.2fs duration", fps, total_frames, duration)

    for ts in timestamps:
        target_frame = min(int(ts * fps), total_frames - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        if ret:
            out_file = output_dir / f"scene01_motion_{int(ts):02d}s.png"
            cv2.imwrite(str(out_file), frame)
            logger.info("Đã trích xuất khung hình %ds (frame %d) -> %s", int(ts), target_frame, out_file.name)
    cap.release()


async def execute():
    dirs = setup_directories(MOVIE_SLUG)
    logger.info("BẮT ĐẦU PIPELINE PHÂN CẢNH 1: ĐẠI TIỆC MỪNG THỌ (00:00 - 00:08)")

    # 1. Định nghĩa 2 khung hình cho Cảnh 1
    frame_definitions = [
        {
            "index": 1,
            "tag": "tiec_tho_toan_canh",
            "role": "START_FRAME",
            "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "prompt": (
                "A wide cinematic master shot of an opulent imperial banquet hall in ancient eastern dynasty, "
                "grand preceptor manor. Warm lantern lighting, red and gold silk drapery, carved wooden dragon throne on an elevated dais. "
                "An authoritative 70-year-old noble statesman with dignified silver beard and wise wrinkled face, "
                "wearing elaborate crimson and gold embroidered silk robes, sits majestically holding a jade wine cup. "
                "Dozens of civil and military court officials in traditional ancient robes kneel respectfully along the grand aisle holding wine goblets. "
                "Cinematic 8k composition, photorealistic, rich depth of field, 16:9 aspect ratio."
            ),
        },
        {
            "index": 2,
            "tag": "can_canh_ly_pham_uong_ruou",
            "role": "END_FRAME",
            "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "prompt": (
                "A medium close-up cinematic portrait of the 70-year-old noble elder statesman in an opulent banquet hall. "
                "He lowers a delicate white jade wine cup from his lips, having just finished drinking fine wine. "
                "With his other hand he gently strokes his neat silver beard, wearing a proud, triumphant, subtle smiling expression "
                "of worldly authority and supreme power. Richly embroidered crimson and gold ancient robes, warm golden lantern bokeh "
                "in the soft background, highly detailed skin texture, silver hair with ornate jade hairpin. "
                "Photorealistic 8k, dramatic cinematic lighting, 16:9 aspect ratio."
            ),
        },
    ]

    video_prompt_8s = (
        "0-3s: Inside the opulent imperial banquet hall illuminated by glowing lanterns, the noble elderly statesman in embroidered crimson robes raises his jade wine cup with commanding dignity. Steadicam tracks slowly forward between rows of kneeling officials raising their goblets. "
        "3-6s: The elderly statesman brings the cup to his lips, gracefully drinking the fine wine in a single smooth draught, while the court officials kowtow and cheer in celebration. "
        "6-8s: Lowering the jade goblet, he gently strokes his silver beard with a proud, triumphant smile of absolute worldly power, settling smoothly into a poised triumphant sitting stance."
    )

    async with aiohttp.ClientSession() as session:
        # Bước 1: Health check
        if not await check_health(session):
            sys.exit(1)

        # Bước 2: Sinh ảnh song song
        logger.info("\n=== BƯỚC 1/6: SINH 2 KHUNG HÌNH (START & END) CHO CẢNH 1 ===")
        sem = asyncio.Semaphore(2)
        gen_tasks = [
            generate_single_image(session, PROJECT_ID, f, sem)
            for f in frame_definitions
        ]
        generated_results = await asyncio.gather(*gen_tasks)

        # Bước 3: Tải ảnh thô và khử logo
        logger.info("\n=== BƯỚC 2/6: TẢI VỀ & KHỬ WATERMARK BẰNG REVERSE ALPHA BLENDING ===")
        processed_frames = []
        for res in generated_results:
            idx = res["index"]
            tag = res["tag"]
            raw_path = dirs["raw"] / f"frame_{idx:02d}_{tag}_raw.png"
            clean_path = dirs["cleaned"] / f"frame_{idx:02d}_{tag}_clean.png"

            await download_image_file(session, res["download_url"], raw_path)
            t_ms = clean_single_watermark(raw_path, clean_path)
            logger.info("Khử logo Frame #%02d [%s] trong %.1fms -> %s", idx, tag, t_ms, clean_path.name)

            processed_frames.append({
                "index": idx,
                "tag": tag,
                "role": res["role"],
                "prompt": res["prompt"],
                "original_flow_media_id": res["original_flow_media_id"],
                "raw_local_path": str(raw_path.resolve()),
                "clean_local_path": str(clean_path.resolve()),
                "uploaded_clean_media_id": None,
            })

        # Bước 4: Upload ảnh sạch lên Google Flow
        logger.info("\n=== BƯỚC 3/6: UPLOAD ẢNH ĐÃ KHỬ SẠCH LOGO LÊN GOOGLE FLOW ===")
        processed_frames.sort(key=lambda x: x["index"])
        upload_tasks = [
            upload_clean_image_task(session, PROJECT_ID, f)
            for f in processed_frames
        ]
        uploaded_frames = await asyncio.gather(*upload_tasks)

        start_clean_id = uploaded_frames[0]["uploaded_clean_media_id"]
        end_clean_id = uploaded_frames[1]["uploaded_clean_media_id"]

        # Bước 5: Kích hoạt sinh video F2F 8s
        logger.info("\n=== BƯỚC 4/6: KÍCH HOẠT TẠO VIDEO 8S FRAME-TO-FRAME (VEO 3.1) ===")
        video_title = f"{MOVIE_SLUG}_scene_01_f2f_8s"
        video_res = await trigger_f2f_video_8s(
            session=session,
            project_id=PROJECT_ID,
            start_mid=start_clean_id,
            end_mid=end_clean_id,
            video_prompt=video_prompt_8s,
            title=video_title,
        )

        op_id = extract_op_id_from_response(video_res)
        logger.info("Đã nhận Operation ID: %s", op_id)

        # Bước 6: Polling và tải video về
        logger.info("\n=== BƯỚC 5/6: THEO DÕI TIẾN ĐỘ RENDER VÀ TẢI CLIP VỀ ===")
        dest_video = dirs["clips"] / "scene_01_tiec_tho_8s.mp4"
        poll_res = await poll_video_until_ready(
            session=session,
            project_id=PROJECT_ID,
            operation_id=op_id,
            max_wait_seconds=480,
            poll_interval=10,
        )

        if poll_res.get("status") == "SUCCESSFUL" and poll_res.get("video_url"):
            logger.info("Đang tải video clip về: %s...", dest_video.name)
            async with session.get(poll_res["video_url"], timeout=120) as vresp:
                if vresp.status == 200:
                    vbytes = await vresp.read()
                    dest_video.write_bytes(vbytes)
                    logger.info("TẢI VIDEO THÀNH CÔNG: %s (%.2f MB)", dest_video.name, len(vbytes) / (1024 * 1024))

            # Bước 7: Trích xuất khung hình chuyển động mẫu
            logger.info("\n=== BƯỚC 6/6: TRÍCH XUẤT CÁC KHUNG HÌNH MẪU ĐỂ ĐÁNH GIÁ ĐỘ MƯỢT ===")
            extract_motion_frames(dest_video, dirs["frames"], [0.0, 2.0, 4.0, 6.0, 8.0])

        logger.info("\n" + "=" * 80)
        logger.info("HOÀN TẤT TOÀN BỘ QUY TRÌNH PHÂN CẢNH 1 XUẤT SẮC!")
        logger.info("  Video File: %s", dest_video)
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(execute())

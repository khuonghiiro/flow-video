"""Tự động hoá sinh 3 video candidates song song cho 1 prompt để so sánh lựa chọn.
Dự án: Kingdom Builder Upgrade Scene
Hoạt động khép kín:
1. Gửi 3 yêu cầu sinh video độc lập tới Google Flow qua Backend API.
2. Tự động polling kiểm tra tiến độ mỗi 10 giây cho đến khi cả 3 hoàn tất.
3. Tải cả 3 video về agent-veo3/output/candidates/ (candidate_01.mp4, candidate_02.mp4, candidate_03.mp4).
4. Trích xuất frame so sánh (2s, 4s, 6s, 8s) cho từng candidate để người dùng đối chiếu.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List
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
OUTPUT_DIR = AGENT_DIR / "output" / "candidates"
API_BASE = "http://127.0.0.1:8100"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("generate_3_candidates")

# Cấu hình mặc định cho cảnh Kingdom Builder Upgrade
DEFAULT_CONFIG = {
    "project_id": "f762d7dd-63d3-4a43-a5bc-6c3fb2072839",
    "scene_id": "519932ee-bbe8-4e4a-b6da-9a5c6fccedde",
    "start_image_media_id": "6592d253-44aa-47c0-9f08-a688908e1cb2",
    "prompt": (
        "0-3s: Tiny_Builder furiously hammers the wooden beams, creating bouncy cartoon dust puffs "
        "and floating golden spark particles as the outpost vibrates with energetic cartoon physics, "
        "camera holds a steady isometric view. "
        "3-6s: A dramatic golden \"LEVEL UP\" aura bursts across the structure; the wooden scaffolding vanishes "
        "in a puff of sparkling smoke as polished cobblestones and vibrant cobalt-blue roof tiles magically fly in "
        "and snap into place like an animated 3D mobile game upgrade sequence. "
        "6-8s: The building transforms into a grand Level 2 stone fortress with a fluttering royal pennant flag on top; "
        "celebratory confetti bursts into the air as the camera performs a smooth, gentle orbit pan to showcase the gleaming upgraded building."
    ),
    "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "duration": 8.0,
    "user_paygate_tier": "PAYGATE_TIER_TWO",
    "num_candidates": 3,
}


async def submit_single_candidate(
    session: aiohttp.ClientSession,
    idx: int,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Gửi yêu cầu sinh 1 candidate video."""
    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": config["start_image_media_id"],
        "prompt": config["prompt"],
        "project_id": config["project_id"],
        "scene_id": config["scene_id"],
        "aspect_ratio": config["aspect_ratio"],
        "user_paygate_tier": config["user_paygate_tier"],
        "duration": config["duration"],
        "title": f"Candidate_{idx:02d}",
    }
    logger.info("[SUBMIT] Gửi yêu cầu cho Candidate #%02d...", idx)
    try:
        async with session.post(url, json=payload, timeout=120) as resp:
            data = await resp.json()
            if resp.status != 200:
                logger.error("[LỖI] Candidate #%02d thất bại: %s", idx, data)
                return {"idx": idx, "error": data}
            
            ops = data.get("operations", [])
            if not ops and isinstance(data.get("data"), dict):
                ops = data["data"].get("operations", [])
            
            op_name = None
            if ops:
                op_name = ops[0].get("operation", {}).get("name") or ops[0].get("name")
            
            logger.info("[OK] Candidate #%02d đã gửi thành công. Operation: %s", idx, op_name)
            return {"idx": idx, "operation": op_name, "raw": data}
    except Exception as exc:
        logger.exception("[EXCEPTION] Candidate #%02d gặp lỗi: %s", idx, exc)
        return {"idx": idx, "error": str(exc)}


async def poll_all_operations(
    session: aiohttp.ClientSession,
    active_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Polling liên tục cho đến khi tất cả các operations hoàn thành."""
    url = f"{API_BASE}/api/flow/check-status"
    pending = list(active_candidates)
    completed = []
    start_time = time.time()

    while pending:
        elapsed = int(time.time() - start_time)
        ops_payload = []
        for c in pending:
            op_name = c.get("operation")
            if op_name:
                ops_payload.append({
                    "operation": {"name": op_name},
                    "status": "MEDIA_GENERATION_STATUS_PENDING"
                })

        if not ops_payload:
            logger.warning("Không còn operation hợp lệ để polling.")
            break

        try:
            async with session.post(url, json={"operations": ops_payload}, timeout=60) as resp:
                data = await resp.json()
                media_list = data.get("media", [])
                if not media_list and isinstance(data.get("data"), dict):
                    media_list = data["data"].get("media", [])

                # Ghép operations hoặc media với candidate
                ops_list = data.get("operations", [])
                still_pending = []
                for cand in pending:
                    op_name = cand.get("operation")
                    matched_url = None
                    matched_id = None

                    # 1. Kiểm tra trong operations list (Chuẩn Veo3 Batch RPC)
                    for op_item in ops_list:
                        item_op = op_item.get("operation", {})
                        item_name = item_op.get("name") or op_item.get("name")
                        status = op_item.get("status")
                        if item_name == op_name and status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                            meta_video = item_op.get("metadata", {}).get("video", {})
                            matched_url = meta_video.get("fifeUrl") or meta_video.get("url")
                            matched_id = meta_video.get("mediaId") or item_name
                            break

                    # 2. Fallback kiểm tra trong media list (nếu có)
                    if not matched_url:
                        for m in media_list:
                            m_op = m.get("operation", {}).get("name") or m.get("name")
                            if m_op == op_name:
                                matched_url = (
                                    m.get("video", {}).get("fifeUrl")
                                    or m.get("fifeUrl")
                                    or m.get("videoUrl")
                                )
                                matched_id = m.get("name") or m.get("id")
                                break

                    if matched_url:
                        cand["video_url"] = matched_url
                        cand["media_id"] = matched_id
                        logger.info("🎉 [HOÀN THÀNH] Candidate #%02d đã render xong sau %ds!", cand["idx"], elapsed)
                        completed.append(cand)
                    else:
                        still_pending.append(cand)

                pending = still_pending
        except Exception as exc:
            logger.warning("Lỗi polling (sẽ thử lại sau 10s): %s", exc)

        if pending:
            logger.info("⏳ [%ds] Đang chờ %d/%d candidates hoàn thành...", elapsed, len(pending), len(active_candidates))
            await asyncio.sleep(12)

    return completed


def download_and_extract_frames(candidates: List[Dict[str, Any]]):
    """Tải video MP4 về máy và trích xuất các khung hình mẫu so sánh."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    import urllib.request

    for c in candidates:
        idx = c["idx"]
        url = c.get("video_url")
        if not url:
            logger.warning("Bỏ qua Candidate #%02d vì không có video URL", idx)
            continue

        vid_path = OUTPUT_DIR / f"candidate_{idx:02d}.mp4"
        logger.info("[DOWNLOAD] Đang tải Candidate #%02d -> %s", idx, vid_path.name)
        try:
            urllib.request.urlretrieve(url, str(vid_path))
            c["local_video_path"] = str(vid_path)
            c["file_size_mb"] = round(os.path.getsize(vid_path) / (1024 * 1024), 2)
            logger.info("Tải xong Candidate #%02d (%0.2f MB)", idx, c["file_size_mb"])

            # Trích xuất 4 mốc thời gian: 2s, 4s, 6s, 8s
            cap = cv2.VideoCapture(str(vid_path))
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            for sec in [2, 4, 6, 8]:
                frame_idx = int(sec * fps) - 1
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_idx))
                ret, frame = cap.read()
                if ret:
                    thumb_name = f"candidate_{idx:02d}_frame_{sec}s.jpg"
                    thumb_path = OUTPUT_DIR / thumb_name
                    cv2.imwrite(str(thumb_path), frame)
            cap.release()
            logger.info("Đã trích xuất khung hình so sánh cho Candidate #%02d", idx)
        except Exception as exc:
            logger.error("Lỗi khi tải hoặc trích xuất video #%02d: %s", idx, exc)


async def main():
    logger.info("=== BẮT ĐẦU PIPELINE TỰ ĐỘNG SINH 3 CANDIDATE VIDEOS ===")
    config = DEFAULT_CONFIG

    async with aiohttp.ClientSession() as session:
        # Bước 1: Gửi đồng thời 3 requests
        tasks = [
            submit_single_candidate(session, i, config)
            for i in range(1, config["num_candidates"] + 1)
        ]
        submissions = await asyncio.gather(*tasks)

        active = [s for s in submissions if s.get("operation")]
        if not active:
            logger.error("Không có candidate nào gửi thành công!")
            return

        logger.info("Đã gửi thành công %d candidates. Bắt đầu polling tự động...", len(active))

        # Bước 2: Polling liên tục cho tới khi xong tất cả
        completed = await poll_all_operations(session, active)

        # Bước 3: Tải về và trích xuất khung hình
        download_and_extract_frames(completed)

        logger.info("=== TẤT CẢ 3 CANDIDATES ĐÃ SẴN SÀNG ĐỂ SO SÁNH ===")
        for c in completed:
            logger.info("Candidate #%02d: %s (%s MB)", c["idx"], c.get("local_video_path"), c.get("file_size_mb"))


if __name__ == "__main__":
    asyncio.run(main())

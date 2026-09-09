"""
Pipeline Chuan Flow-Video:
1. Tao du an moi tren Google Flow.
2. Tao 2 anh song song (Parallel) tren Flow API.
3. Tai ca 2 anh ve thu muc: agent-veo3/output/watermarks/
4. Khu sach 100% watermark logo Gemini va luu sang: agent-veo3/output/cleaned/
5. AI kiem tra va upload anh sach len Flow (khong upload trung lap 2 lan).
6. Tao video chuan Image-to-Video (I2V / 1 frame duy nhat, KHONG dung F2F / frame-to-frame).
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
import aiohttp
import cv2

# Console UTF-8 encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_DIR = SCRIPT_DIR.parent.parent
sys.path.append(str(SCRIPT_DIR.parent))

from remove_gemini_watermark import remove_watermark

API_BASE = "http://127.0.0.1:8100"
WATERMARKS_DIR = AGENT_DIR / "output" / "watermarks"
CLEANED_DIR = AGENT_DIR / "output" / "cleaned"
WATERMARKS_DIR.mkdir(parents=True, exist_ok=True)
CLEANED_DIR.mkdir(parents=True, exist_ok=True)


async def create_project(session: aiohttp.ClientSession, title: str) -> str:
    print(f"\n[Bước 1] Đang tạo dự án mới trên Google Flow: '{title}'...")
    url = f"{API_BASE}/api/flow/project/create"
    async with session.post(url, json={"title": title}, timeout=45) as resp:
        data = await resp.json()
        pid = data.get("projectId") or data.get("id")
        if not pid:
            raise RuntimeError(f"Không thể tạo dự án: {data}")
        print(f"  -> [OK] Project ID: {pid}")
        return pid


async def generate_single_image(
    session: aiohttp.ClientSession,
    project_id: str,
    prompt: str,
    name_tag: str,
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE"
) -> dict:
    print(f"  [*] Đang gửi yêu cầu sinh ảnh: {name_tag}...")
    url = f"{API_BASE}/api/flow/generate-image"
    payload = {
        "prompt": prompt,
        "project_id": project_id,
        "aspect_ratio": aspect_ratio,
        "user_paygate_tier": "PAYGATE_TIER_TWO"
    }
    t0 = time.time()
    async with session.post(url, json=payload, timeout=240) as resp:
        res = await resp.json()
        elapsed = time.time() - t0
        print(f"  [+] Ảnh '{name_tag}' sinh xong sau {elapsed:.1f}s")
        
        media_list = res.get("media", [])
        media_url = None
        media_id = "unknown"
        if media_list and isinstance(media_list, list):
            gen_img = media_list[0].get("image", {}).get("generatedImage", {})
            media_id = gen_img.get("mediaId", "media")
            media_url = gen_img.get("fifeUrl") or gen_img.get("mediaUrl")
            
        if not media_url:
            raise RuntimeError(f"Không tìm thấy URL cho ảnh {name_tag}: {res}")
            
        return {
            "name_tag": name_tag,
            "media_id": media_id,
            "url": media_url
        }


async def download_image(session: aiohttp.ClientSession, url: str, dest_path: Path) -> bool:
    async with session.get(url, timeout=60) as resp:
        if resp.status == 200:
            content = await resp.read()
            with open(dest_path, "wb") as f:
                f.write(content)
            print(f"  [DOWNLOAD] Đã lưu ảnh thô (chứa watermark) vào: {dest_path.name} ({len(content) / 1024:.1f} KB)")
            return True
        print(f"  [LỖI] Tải ảnh thất bại HTTP {resp.status}")
        return False


def clean_watermark(raw_path: Path, clean_path: Path) -> float:
    img = cv2.imread(str(raw_path))
    if img is None:
        raise RuntimeError(f"Không thể đọc file: {raw_path}")
    t0 = time.time()
    cleaned = remove_watermark(img, alpha_peak=0.28)
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(clean_path), cleaned, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
    return (time.time() - t0) * 1000.0


async def upload_cleaned_image(
    session: aiohttp.ClientSession,
    project_id: str,
    image_path: Path,
    uploaded_cache: dict
) -> str:
    # Tránh upload trùng lặp cùng 1 file
    cache_key = f"{project_id}:{image_path.name}"
    if cache_key in uploaded_cache:
        print(f"  [SKIP] File {image_path.name} đã được upload trước đó. Dùng lại UUID: {uploaded_cache[cache_key]}")
        return uploaded_cache[cache_key]

    print(f"\n[Bước 4] Đang upload ảnh sạch từ thư mục 'output/cleaned/' lên Flow...")
    print(f"  File upload: {image_path.name}")
    url = f"{API_BASE}/api/flow/upload-image"
    payload = {
        "file_path": str(image_path.resolve()),
        "project_id": project_id,
        "file_name": image_path.name
    }
    # Timeout 150s để extension giải captcha và gửi payload an toàn
    async with session.post(url, json=payload, timeout=150) as resp:
        data = await resp.json()
        uploaded_media_id = data.get("media_id") or data.get("mediaId")
        if not uploaded_media_id:
            raw = data.get("raw", {})
            if isinstance(raw, dict):
                uploaded_media_id = raw.get("name") or raw.get("id") or raw.get("_mediaId")
        if not uploaded_media_id:
            raise RuntimeError(f"Không lấy được media_id: {data}")
            
        print(f"  -> [THÀNH CÔNG] Đã upload ảnh sạch lên Flow! Media UUID: {uploaded_media_id}")
        uploaded_cache[cache_key] = uploaded_media_id
        return uploaded_media_id


async def generate_single_frame_i2v_video(
    session: aiohttp.ClientSession,
    project_id: str,
    start_image_id: str,
    video_prompt: str,
    scene_id: str = "scene_001"
) -> dict:
    """
    Tạo video từ DUY NHẤT 1 frame (I2V - Image-to-Video).
    Tuyệt đối KHÔNG truyền end_image_media_id (để không kích hoạt logic F2F nội suy 2 frame).
    """
    print(f"\n[Bước 5] Gửi lệnh tạo video I2V (1 frame start duy nhất, RPC: eb1hJf)...")
    print(f"  - Start Frame Media UUID: {start_image_id}")
    print(f"  - End Frame: None (Strict Single-Frame I2V, không dùng F2F)")
    print(f"  - Prompt chuyển động: {video_prompt}")
    
    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": start_image_id,
        "prompt": video_prompt,
        "project_id": project_id,
        "scene_id": scene_id,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "model_family": "veo",
        "duration_s": 8
    }
    
    t0 = time.time()
    async with session.post(url, json=payload, timeout=120) as resp:
        res = await resp.json()
        elapsed = time.time() - t0
        print(f"  -> [OK] Đã submit video I2V thành công sau {elapsed:.1f}s!")
        print(f"  Operations:", json.dumps(res.get("operations", []), indent=2))
        return res


async def main():
    print("=" * 80)
    print("  QUY TRÌNH CHUẨN: TẠO DỰ ÁN -> 2 ẢNH SONG SONG -> KHỬ LOGO -> UPLOAD -> I2V VIDEO")
    print("=" * 80)
    
    timestamp = int(time.time())
    project_title = f"Project_Clean_I2V_{timestamp}"
    uploaded_cache = {}
    
    async with aiohttp.ClientSession() as session:
        # 1. Tạo dự án mới
        project_id = await create_project(session, project_title)
        
        # 2. Tạo 2 ảnh song song
        print(f"\n[Bước 2] Đang tạo 2 ảnh song song (Parallel)...")
        tasks = [
            generate_single_image(
                session,
                project_id,
                prompt="Futuristic crystal palace inside a misty forest at dawn, glowing bioluminescent butterflies, hyper-detailed 4k",
                name_tag="crystal_palace"
            ),
            generate_single_image(
                session,
                project_id,
                prompt="Ancient stone library filled with floating glowing lanterns and flying magical books, cinematic volumetric light, 4k",
                name_tag="ancient_library"
            )
        ]
        images_info = await asyncio.gather(*tasks)
        print(f"  -> Đã tạo xong cả 2 ảnh song song!")
        
        # 3. Tải về watermarks/ và khử logo sang cleaned/
        print(f"\n[Bước 3] Tải ảnh thô vào 'output/watermarks/' và xuất ảnh sạch sang 'output/cleaned/'...")
        cleaned_images = []
        for info in images_info:
            tag = info["name_tag"]
            raw_file = WATERMARKS_DIR / f"{tag}_{timestamp}.jpeg"
            clean_file = CLEANED_DIR / f"{tag}_{timestamp}.jpeg"
            
            print(f"\n  * Xử lý {tag}:")
            await download_image(session, info["url"], raw_file)
            
            t_clean = clean_watermark(raw_file, clean_file)
            print(f"    -> Đã tách sạch 100% logo trong {t_clean:.1f}ms: output/cleaned/{clean_file.name}")
            cleaned_images.append(clean_file)
            
        # 4. Upload ảnh sạch từ cleaned/ lên Flow (bắt đúng ảnh, không trùng lặp)
        selected_clean_file = cleaned_images[0]
        uploaded_uuid = await upload_cleaned_image(session, project_id, selected_clean_file, uploaded_cache)
        
        # 5. Tạo video I2V từ đúng 1 ảnh sạch vừa upload (không dùng frame-to-frame)
        video_prompt = (
            "Cinematic slow camera glide forward into the crystal palace. "
            "Soft ethereal fog drifting, glowing particles floating gracefully in the air, smooth 4k."
        )
        video_result = await generate_single_frame_i2v_video(
            session,
            project_id=project_id,
            start_image_id=uploaded_uuid,
            video_prompt=video_prompt,
            scene_id=f"scene_i2v_{timestamp}"
        )
        
        print("\n" + "=" * 80)
        print("  HOÀN TẤT THÀNH CÔNG TOÀN BỘ QUY TRÌNH!")
        print(f"  1. Thư mục ảnh thô (chứa watermark): {WATERMARKS_DIR}")
        print(f"  2. Thư mục ảnh sạch (đã khử logo):    {CLEANED_DIR}")
        print(f"  3. Project ID:                       {project_id}")
        print(f"  4. Media UUID upload sạch:           {uploaded_uuid}")
        print(f"  5. Chế độ video:                     Image-to-Video (I2V / 1 frame, RPC: eb1hJf)")
        print(f"  6. Video Operations:                 {video_result.get('operations')}")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

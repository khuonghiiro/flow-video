"""
Full End-to-End Pipeline Test:
1. Create new project on Google Flow via API.
2. Generate 2 images in parallel via Flow API.
3. Download both images to agent-veo3/output.
4. Remove watermark cleanly from both images via Reverse Alpha Blending.
5. Upload the cleaned image back to Google Flow to obtain a new media UUID.
6. Trigger Veo video generation from the uploaded clean image.
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
import aiohttp
import cv2

# Reconfigure console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add parent scripts dir to import remove_watermark
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_PARENT = SCRIPT_DIR.parent
sys.path.append(str(SCRIPTS_PARENT))

from remove_gemini_watermark import remove_watermark

API_BASE = "http://127.0.0.1:8100"
OUTPUT_DIR = SCRIPTS_PARENT.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def create_project(session: aiohttp.ClientSession, title: str) -> str:
    print(f"\n[Bước 1] Đang tạo dự án mới trên Google Flow: '{title}'...")
    url = f"{API_BASE}/api/flow/project/create"
    async with session.post(url, json={"title": title}, timeout=30) as resp:
        data = await resp.json()
        pid = data.get("projectId") or data.get("id")
        if not pid:
            raise RuntimeError(f"Không thể tạo dự án: {data}")
        print(f"  [THÀNH CÔNG] Project ID: {pid}")
        return pid


async def generate_single_image(
    session: aiohttp.ClientSession,
    project_id: str,
    prompt: str,
    name_tag: str,
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE"
) -> dict:
    print(f"  [*] Bắt đầu sinh ảnh: {name_tag}...")
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
            print(f"  [DOWNLOAD] Đã tải về: {dest_path.name} ({len(content) / 1024:.1f} KB)")
            return True
        print(f"  [LỖI] Tải ảnh thất bại HTTP {resp.status}")
        return False


def clean_watermark(raw_path: Path, clean_path: Path) -> float:
    img = cv2.imread(str(raw_path))
    if img is None:
        raise RuntimeError(f"Không thể đọc file ảnh: {raw_path}")
    t0 = time.time()
    cleaned = remove_watermark(img, alpha_peak=0.28)
    cv2.imwrite(str(clean_path), cleaned, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
    return (time.time() - t0) * 1000.0


async def upload_cleaned_image(session: aiohttp.ClientSession, project_id: str, image_path: Path) -> str:
    print(f"\n[Bước 4] Đang upload ảnh sạch (đã khử logo) ngược lại Google Flow...")
    url = f"{API_BASE}/api/flow/upload-image"
    payload = {
        "file_path": str(image_path.resolve()),
        "project_id": project_id,
        "file_name": image_path.name
    }
    async with session.post(url, json=payload, timeout=60) as resp:
        data = await resp.json()
        uploaded_media_id = data.get("media_id") or data.get("mediaId")
        if not uploaded_media_id:
            # Check inside raw
            raw = data.get("raw", {})
            if isinstance(raw, dict):
                uploaded_media_id = raw.get("name") or raw.get("id") or raw.get("_mediaId")
        if not uploaded_media_id:
            raise RuntimeError(f"Không lấy được media_id sau khi upload: {data}")
        print(f"  [THÀNH CÔNG] Đã upload ảnh sạch lên Flow! Media UUID mới: {uploaded_media_id}")
        return uploaded_media_id


async def generate_video_from_uploaded(
    session: aiohttp.ClientSession,
    project_id: str,
    start_image_id: str,
    video_prompt: str
) -> dict:
    print(f"\n[Bước 5] Đang gửi yêu cầu tạo video từ ảnh sạch vừa upload (UUID: {start_image_id})...")
    print(f"  Prompt chuyển động: {video_prompt}")
    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": start_image_id,
        "prompt": video_prompt,
        "project_id": project_id,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "duration_s": 4,
        "quality": "720p",
        "count": 1
    }
    t0 = time.time()
    async with session.post(url, json=payload, timeout=120) as resp:
        res = await resp.json()
        elapsed = time.time() - t0
        print(f"  [THÀNH CÔNG] Video submit thành công sau {elapsed:.1f}s!")
        print(f"  Kết quả video:", json.dumps(res, indent=2))
        return res


async def main():
    print("=" * 75)
    print("   END-TO-END PIPELINE: TẠO DỰ ÁN -> 2 ẢNH SONG SONG -> KHỬ LOGO -> UPLOAD -> VIDEO")
    print("=" * 75)
    
    timestamp = int(time.time())
    project_title = f"Test_Unwatermark_Flow_{timestamp}"
    
    async with aiohttp.ClientSession() as session:
        # 1. Tạo dự án mới
        project_id = await create_project(session, project_title)
        
        # 2. Tạo 2 ảnh song song
        print(f"\n[Bước 2] Đang gửi yêu cầu tạo 2 ảnh song song (Parallel)...")
        tasks = [
            generate_single_image(
                session,
                project_id,
                prompt="Cyberpunk neon city street in rain, reflections on wet asphalt, glowing billboards, flying spinner vehicles, cinematic 4k",
                name_tag="cyberpunk_city"
            ),
            generate_single_image(
                session,
                project_id,
                prompt="Serene Japanese zen garden in autumn, red maple leaves falling over stone lanterns and koi pond, soft morning mist, photorealistic 4k",
                name_tag="zen_garden"
            )
        ]
        
        images_info = await asyncio.gather(*tasks)
        print(f"  [THÀNH CÔNG] Đã sinh xong cả 2 ảnh song song!")
        
        # 3. Tải về và Khử watermark
        print(f"\n[Bước 3] Tải ảnh về thư mục output và khử watermark bằng Reverse Alpha Blending...")
        cleaned_files = []
        for info in images_info:
            tag = info["name_tag"]
            raw_path = OUTPUT_DIR / f"{tag}_{timestamp}.jpeg"
            clean_path = OUTPUT_DIR / f"{tag}_{timestamp}_cleaned.jpeg"
            
            print(f"\n  * Đang tải {tag}...")
            await download_image(session, info["url"], raw_path)
            
            t_clean = clean_watermark(raw_path, clean_path)
            print(f"    -> Đã khử sạch logo {tag} trong {t_clean:.1f}ms: {clean_path.name}")
            cleaned_files.append((tag, clean_path))
            
        # 4. Upload 1 ảnh sạch (ví dụ ảnh cyberpunk) lên lại Google Flow
        target_tag, target_clean_file = cleaned_files[0]
        uploaded_uuid = await upload_cleaned_image(session, project_id, target_clean_file)
        
        # 5. Tạo video từ ảnh đã upload
        video_prompt = (
            "Slow cinematic camera dolly push forward along the wet street. "
            "Gentle atmospheric rain falling, soft flickering of pink and blue neon lights, no sudden camera shake."
        )
        video_result = await generate_video_from_uploaded(session, project_id, uploaded_uuid, video_prompt)
        
        print("\n" + "=" * 75)
        print("  HOÀN THÀNH TOÀN BỘ QUY TRÌNH END-TO-END THÀNH CÔNG!")
        print(f"  - Project ID: {project_id}")
        print(f"  - Ảnh 1 (sạch): {cleaned_files[0][1]}")
        print(f"  - Ảnh 2 (sạch): {cleaned_files[1][1]}")
        print(f"  - Media UUID đã upload: {uploaded_uuid}")
        print(f"  - Video Task Submitted: Đang render trên Veo")
        print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())

"""
End-to-End Test:
1. Generate test image via Google Flow API.
2. Download to agent-veo3/output.
3. Automatically detect and remove Gemini watermark while preserving pixel sharpness.
"""

import os
import sys
import time
import json
import urllib.request
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from remove_gemini_watermark import remove_watermark
import cv2

API_BASE = "http://127.0.0.1:8100"
PROJECT_ID = "54c61872-79ae-4024-b521-803be620756c"
OUTPUT_DIR = Path(r"D:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def post_json(endpoint: str, data: dict, timeout: int = 180) -> dict:
    url = f"{API_BASE}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, dest_path: Path) -> bool:
    try:
        urllib.request.urlretrieve(url, str(dest_path))
        print(f"  [DOWNLOAD] Saved {dest_path.name} ({dest_path.stat().st_size / 1024:.1f} KB)")
        return True
    except Exception as e:
        print(f"  [ERROR] Download failed for {url}: {e}")
        return False


def test_generate_and_clean(prompt: str, name_tag: str, aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE"):
    print("=" * 65)
    print(f"[*] Bắt đầu tạo ảnh: {name_tag}")
    print(f"    Prompt: {prompt}")
    print(f"    Aspect: {aspect_ratio}")
    print("=" * 65)

    payload = {
        "prompt": prompt,
        "project_id": PROJECT_ID,
        "aspect_ratio": aspect_ratio,
        "user_paygate_tier": "PAYGATE_TIER_TWO"
    }

    t0 = time.time()
    try:
        res = post_json("/api/flow/generate-image", payload, timeout=180)
    except Exception as e:
        print(f"[!] Lỗi gọi API tạo ảnh: {e}")
        return None

    elapsed = time.time() - t0
    print(f"[+] API trả về sau {elapsed:.1f}s")

    # Extract media URL
    media_url = None
    media_id = "unknown"
    media_list = res.get("media", [])
    if media_list and isinstance(media_list, list):
        gen_img = media_list[0].get("image", {}).get("generatedImage", {})
        media_id = gen_img.get("mediaId", "media")
        media_url = gen_img.get("fifeUrl") or gen_img.get("mediaUrl")

    if not media_url:
        print(f"[!] Không tìm thấy URL ảnh trong phản hồi: {res}")
        return None

    timestamp = int(time.time())
    raw_filename = f"{name_tag}_{timestamp}.jpeg"
    raw_path = OUTPUT_DIR / raw_filename
    cleaned_filename = f"{name_tag}_{timestamp}_cleaned.jpeg"
    cleaned_path = OUTPUT_DIR / cleaned_filename

    # Download raw image
    print(f"[*] Đang tải ảnh gốc có logo về output...")
    if not download_file(media_url, raw_path):
        return None

    # Apply watermark removal
    print(f"[*] Đang chạy thuật toán Reverse Alpha Blending để khử logo...")
    img = cv2.imread(str(raw_path))
    if img is None:
        print(f"[!] Không đọc được ảnh: {raw_path}")
        return None

    t_clean_0 = time.time()
    cleaned = remove_watermark(img, alpha_peak=0.28)
    cv2.imwrite(str(cleaned_path), cleaned, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
    clean_time = (time.time() - t_clean_0) * 1000

    print(f"[SUCCESS] Hoàn tất khử logo trong {clean_time:.1f}ms!")
    print(f"    - Ảnh gốc (có logo): {raw_path}")
    print(f"    - Ảnh sạch (không logo): {cleaned_path}")

    return raw_path, cleaned_path


def main():
    prompt = (
        "A breathtaking snowy mountain peak under a vibrant starry night sky with Milky Way galaxy, "
        "calm alpine lake reflecting the stars, pine trees on foreground, cinematic lighting, ultra-sharp 4K photorealistic"
    )
    test_generate_and_clean(prompt, "mountain_stars", "IMAGE_ASPECT_RATIO_LANDSCAPE")


if __name__ == "__main__":
    main()

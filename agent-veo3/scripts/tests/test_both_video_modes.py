"""
Test ca 2 che do tao video theo dung log bat duoc tren Google Flow:
1. Tao video voi anh (Image-to-Video / R2V): RPC MZZa6b (veo_3_1_r2v_lite_low_priority)
2. Tao video frame to frame (F2F): RPC nprQif (veo_3_1_interpolation_lite_low_priority)
"""

import sys
import json
import time
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://127.0.0.1:8100"
PROJECT_ID = "7f80f456-ce4f-4398-a3f4-0c25914c2bac"
CLEANED_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "cleaned"


def upload_image(file_path: Path) -> str:
    print(f"\n[*] Uploading clean image: {file_path.name}...")
    url = f"{API_BASE}/api/flow/upload-image"
    payload = {
        "file_path": str(file_path.resolve()),
        "project_id": PROJECT_ID,
        "file_name": file_path.name
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=150) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        mid = data.get("media_id") or data.get("raw", {}).get("name")
        print(f"  -> Uploaded media UUID: {mid}")
        return mid


def test_r2v_single_image(media_id: str):
    print("\n" + "=" * 75)
    print("  TEST 1: TẠO VIDEO VỚI ẢNH (RPC: MZZa6b — theo log 'tạo video với ảnh - dọc.txt')")
    print("=" * 75)
    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": media_id,
        "prompt": "Cinematic camera push forward through glowing crystal palace, particles floating, 4k",
        "project_id": PROJECT_ID,
        "scene_id": "scene_r2v_test",
        "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "duration_s": 8
    }
    t0 = time.time()
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=150) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - t0
        print(f"  [THÀNH CÔNG] Đã submit video với ảnh sau {elapsed:.1f}s!")
        print("  Operations:", json.dumps(res.get("operations", []), indent=2))
        return res


def test_f2f_two_frames(start_id: str, end_id: str):
    print("\n" + "=" * 75)
    print("  TEST 2: TẠO VIDEO FRAME TO FRAME (RPC: nprQif — theo log 'tạo video với frame to frame - dọc.txt')")
    print("=" * 75)
    print(f"  Start Frame: {start_id}")
    print(f"  End Frame:   {end_id}")
    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": start_id,
        "end_image_media_id": end_id,
        "prompt": "Cinematic transition from crystal palace into magical library, flying lanterns and glowing mist, 4k",
        "project_id": PROJECT_ID,
        "scene_id": "scene_f2f_test",
        "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "duration_s": 8
    }
    t0 = time.time()
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=150) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - t0
        print(f"  [THÀNH CÔNG] Đã submit video Frame-to-Frame sau {elapsed:.1f}s!")
        print("  Operations:", json.dumps(res.get("operations", []), indent=2))
        return res


def main():
    print("Kiem tra file anh sach trong output/cleaned/...")
    crystal_file = CLEANED_DIR / "crystal_palace_1788948004.jpeg"
    ancient_file = CLEANED_DIR / "ancient_library_1788948004.jpeg"

    if not crystal_file.exists() or not ancient_file.exists():
        print(f"Loi: Chua tim thay anh sach trong {CLEANED_DIR}")
        return

    # Frame 1: crystal palace (da upload trước hoặc upload mới)
    start_uuid = "2c3fe276-3afe-4403-8fa0-dbe53797ebaa"

    # Test 1: Tạo video với 1 ảnh sạch duy nhất (RPC MZZa6b)
    test_r2v_single_image(start_uuid)

    # Frame 2: Upload ảnh sạch thứ hai ancient_library để test Frame-to-Frame
    end_uuid = upload_image(ancient_file)

    # Test 2: Tạo video Frame-to-Frame với CẢ 2 FRAME (RPC nprQif)
    test_f2f_two_frames(start_uuid, end_uuid)


if __name__ == "__main__":
    main()

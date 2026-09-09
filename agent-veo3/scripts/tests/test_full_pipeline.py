"""Full E2E Test: Project → Images → R2V x2 → F2F x2 (all 8s).

Run: $env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe scripts/test_full_pipeline.py
"""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8100"


def api(method, path, body=None, timeout=120):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(body_text)
        except Exception:
            return e.code, {"raw": body_text[:500]}
    except Exception as e:
        return 0, {"error": str(e)}


def extract_media_id(result):
    """Extract media_id from image generation result."""
    media = result.get("media", [])
    if media:
        return media[0].get("image", {}).get("generatedImage", {}).get("mediaId", "")
    return ""


def extract_operations(result):
    """Extract operation list from video result."""
    data = result.get("data", result)
    return data.get("operations", [])


def main():
    print("=" * 60)
    print("  FULL E2E PIPELINE TEST")
    print("  Project -> Images -> R2V x2 -> F2F x2 (all 8s)")
    print("=" * 60)

    # ── Step 1: Create Project ──────────────────────────────────
    print("\n[1/5] Tao du an moi...")
    status, proj = api("POST", "/api/projects", {
        "name": "Test Full Pipeline",
        "entities": [
            {"name": "GoldenDog", "description": "A golden retriever puppy", "orientation": "LANDSCAPE"},
        ]
    })
    if status != 200:
        print(f"  LOI: {status} - {proj}")
        return
    pid = proj["id"]
    print(f"  OK! Project ID: {pid}")

    # ── Step 2: Generate Image 1 (Start frame) ─────────────────
    print("\n[2/5] Tao anh 1 (start frame)...")
    status, img1 = api("POST", "/flow/generate-image", {
        "prompt": "A golden retriever puppy sitting calmly in a sunlit garden, looking at camera, photorealistic, 4K",
        "project_id": pid,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
    })
    if status != 200:
        print(f"  LOI: {status} - {img1}")
        return
    media_id_1 = extract_media_id(img1)
    print(f"  OK! Media ID 1: {media_id_1}")

    # Wait a bit between image requests
    time.sleep(3)

    # ── Step 3: Generate Image 2 (End frame) ────────────────────
    print("\n[3/5] Tao anh 2 (end frame)...")
    status, img2 = api("POST", "/flow/generate-image", {
        "prompt": "A golden retriever puppy running joyfully through a flower meadow, action shot, photorealistic, 4K",
        "project_id": pid,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
    })
    if status != 200:
        print(f"  LOI: {status} - {img2}")
        return
    media_id_2 = extract_media_id(img2)
    print(f"  OK! Media ID 2: {media_id_2}")

    time.sleep(3)

    # ── Step 4: R2V — Video tu anh tham chieu x2, 8s ───────────
    print("\n[4/5] Tao video tu anh tham chieu (R2V) x2, 8s, landscape...")
    print(f"  RPC: MZZa6b | Model: veo_3_1_r2v_lite_low_priority")
    print(f"  Reference image: {media_id_1}")
    status, r2v = api("POST", "/flow/generate-video-refs", {
        "reference_media_ids": [media_id_1],
        "prompt": "A golden retriever puppy playfully chasing butterflies in a sunlit garden, camera slowly tracking the puppy, warm golden hour lighting, cinematic 4K",
        "project_id": pid,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "count": 2,
    })
    r2v_ops = extract_operations(r2v)
    print(f"  Status: {status}")
    print(f"  Operations: {len(r2v_ops)}")
    for op in r2v_ops:
        print(f"    - {op.get('operation', {}).get('name', '?')}")
    if status != 200:
        print(f"  LOI R2V: {r2v}")

    time.sleep(3)

    # ── Step 5: F2F — Noi frame video x2, 8s ───────────────────
    print("\n[5/5] Noi frame video (F2F) x2, 8s, landscape...")
    print(f"  RPC: nprQif | Model: veo_3_1_interpolation_lite_low_priority")
    print(f"  Start frame: {media_id_1}")
    print(f"  End frame:   {media_id_2}")
    status, f2f = api("POST", "/flow/generate-video", {
        "start_image_media_id": media_id_1,
        "end_image_media_id": media_id_2,
        "prompt": "The puppy smoothly transitions from sitting still to running forward, camera follows the action, cinematic slow motion",
        "project_id": pid,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "duration": 8,
        "duration_s": 8,
        "model_family": "veo",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "count": 2,
    })
    f2f_ops = extract_operations(f2f)
    print(f"  Status: {status}")
    print(f"  Operations: {len(f2f_ops)}")
    for op in f2f_ops:
        print(f"    - {op.get('operation', {}).get('name', '?')}")
    if status != 200:
        print(f"  LOI F2F: {f2f}")

    # ── Summary ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  KET QUA TONG HOP")
    print("=" * 60)
    print(f"  Project:  {pid}")
    print(f"  Anh 1:    {media_id_1}")
    print(f"  Anh 2:    {media_id_2}")
    print(f"  R2V x2:   {'OK' if status == 200 and r2v_ops else 'LOI'} ({len(r2v_ops)} ops)")
    print(f"  F2F x2:   {'OK' if status == 200 and f2f_ops else 'LOI'} ({len(f2f_ops)} ops)")
    print(f"\n  Tat ca video dang tao tren Flow. Kiem tra tai:")
    print(f"  https://flow.google.com/project/{pid}")


if __name__ == "__main__":
    main()

import sys
import json
import urllib.request

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://127.0.0.1:8100"
PROJECT_ID = "7f80f456-ce4f-4398-a3f4-0c25914c2bac"
START_IMAGE_MEDIA_ID = "2c3fe276-3afe-4403-8fa0-dbe53797ebaa"

def main():
    print("=== GUI LENH TAO VIDEO I2V (1 FRAME START DUY NHAT) ===", flush=True)
    print(f"Project ID: {PROJECT_ID}", flush=True)
    print(f"Start Image UUID: {START_IMAGE_MEDIA_ID}", flush=True)

    url = f"{API_BASE}/api/flow/generate-video"
    payload = {
        "start_image_media_id": START_IMAGE_MEDIA_ID,
        "prompt": "Cinematic slow camera glide forward into the crystal palace. Soft ethereal fog drifting, glowing particles floating gracefully in the air, smooth 4k.",
        "project_id": PROJECT_ID,
        "scene_id": "scene_crystal_001",
        "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "model_family": "veo",
        "duration_s": 8
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("\n[THANH CONG] Da submit video I2V!", flush=True)
            print("Response:", json.dumps(data, indent=2), flush=True)
    except Exception as e:
        print(f"\n[LOI]: {e}", flush=True)

if __name__ == "__main__":
    main()

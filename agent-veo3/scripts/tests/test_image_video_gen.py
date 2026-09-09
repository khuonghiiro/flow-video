"""Test script: generate image and 4s loop video via Flow API."""
import json
import sys
import time
import urllib.request
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://127.0.0.1:8100"

def post_json(endpoint: str, data: dict) -> dict:
    url = f"{API_BASE}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        print(f"[!] HTTP {err.code} on {endpoint}: {body}")
        raise

def get_json(endpoint: str) -> dict:
    url = f"{API_BASE}{endpoint}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    project_id = "ac1379d8-5d3d-4868-8aaa-8b9a5ccc7997"
    try:
        details = get_json("/flow/extension-details")
        for t in details.get("result", {}).get("tabs", []):
            url = t.get("url", "")
            if "/project/" in url:
                project_id = url.split("/project/")[1].split("/")[0].split("?")[0]
                break
    except Exception:
        pass
    print(f"[*] Starting test with project_id: {project_id}")

    # Step 1: Check server and extension (wait if waking up)
    for _ in range(5):
        health = get_json("/health")
        if health.get("extension_connected"):
            break
        time.sleep(2)
    print(f"[*] Server health: extension_connected={health.get('extension_connected')}")
    if not health.get("extension_connected"):
        print("[!] ERROR: Extension is NOT connected!")
        return

    # Step 2: Generate Image
    img_prompt = "cyberpunk martial artist, heroic stance, front view, green background #00FF00, 3D character render, unreal engine 5"
    print(f"\n[1/3] Calling /flow/generate-image...")
    print(f"      Prompt: {img_prompt[:60]}...")
    t0 = time.time()
    img_res = post_json("/api/flow/generate-image", {
        "prompt": img_prompt,
        "project_id": project_id,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_ONE"
    })
    elapsed_img = time.time() - t0
    print(f"      Image response received in {elapsed_img:.1f}s")
    
    # Extract image media_id
    image_media_id = None
    media_list = img_res.get("media", [])
    if media_list and isinstance(media_list, list):
        image_media_id = media_list[0].get("name") or media_list[0].get("id")
    if not image_media_id and "id" in img_res:
        image_media_id = img_res["id"]
    if not image_media_id and "image_media_id" in img_res:
        image_media_id = img_res["image_media_id"]

    print(f"[OK] Image Media ID: {image_media_id}", flush=True)
    if not image_media_id:
        print(f"[!] Full Image Response: {json.dumps(img_res, indent=2)[:300]}", flush=True)
        return

    # Step 3: Generate Video (4s Loop: start_frame == end_frame)
    vid_prompt = "seamless idle loop, breathing motion, martial arts stance, perfectly looped"
    print(f"\n[2/3] Calling /flow/generate-video (4s Seamless Loop)...", flush=True)
    print(f"      start_image_media_id = {image_media_id}", flush=True)
    print(f"      end_image_media_id   = {image_media_id}", flush=True)
    print(f"      duration             = 4.0s", flush=True)
    t1 = time.time()
    vid_res = post_json("/flow/generate-video", {
        "start_image_media_id": image_media_id,
        "end_image_media_id": image_media_id,
        "prompt": vid_prompt,
        "project_id": project_id,
        "scene_id": str(uuid.uuid4()),
        "duration": 4.0,
        "duration_s": 4,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_ONE"
    })
    elapsed_vid = time.time() - t1
    print(f"      Video submission acknowledged in {elapsed_vid:.1f}s", flush=True)

    # Extract primary media ID and workflow
    workflows = vid_res.get("workflows", [])
    vid_media_id = None
    if workflows and isinstance(workflows, list):
        wf0 = workflows[0]
        meta = wf0.get("metadata", {})
        vid_media_id = meta.get("primaryMediaId") or wf0.get("primaryMediaId")
    if not vid_media_id:
        vmedia = vid_res.get("media", [])
        if vmedia and isinstance(vmedia, list):
            vid_media_id = vmedia[0].get("name")

    print(f"[OK] Video Primary Media ID: {vid_media_id}", flush=True)
    print(f"     Workflows count: {len(workflows)}", flush=True)

    # Step 4: Poll video render completion
    print(f"\n[3/3] Polling video render completion...", flush=True)
    for i in range(30):  # Poll up to ~2.5 minutes
        time.sleep(5)
        try:
            url_res = get_json(f"/flow/media-redirect-url/{vid_media_id}")
            vdata = url_res.get("data", {})
            vurl = vdata.get("url", "")
            if vurl and not url_res.get("error"):
                print(f"\n[SUCCESS] Video rendered successfully in ~{(i+1)*5}s!", flush=True)
                print(f"    Media ID:  {vid_media_id}", flush=True)
                print(f"    Video URL: {vurl[:80]}...", flush=True)
                print(f"    Type:      {vdata.get('contentType', 'video/mp4')}", flush=True)
                return
        except Exception:
            pass
        print(f"    ... waiting for Google Cloud render ({(i+1)*5}s elapsed)", flush=True)

    print("\n[!] Polling timed out (video is still rendering in Google Cloud background).")

if __name__ == "__main__":
    main()

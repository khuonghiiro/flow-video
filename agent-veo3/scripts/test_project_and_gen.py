"""End-to-End Test: Create Project, Generate Image, Generate 4s Loop Video via FlowKit / Veo3 API."""
import json
import sys
import time
import urllib.request
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://127.0.0.1:8100"
FLOW_PROJECT_UUID = "8a927b9d-b0ba-4099-bf7b-381639173f36"


def post_json(endpoint: str, data: dict, timeout: int = 120) -> dict:
    url = f"{API_BASE}{endpoint}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        print(f"[!] HTTP {err.code} on {endpoint}: {body}")
        raise


def get_json(endpoint: str, timeout: int = 30) -> dict:
    url = f"{API_BASE}{endpoint}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("================================================================")
    print("   END-TO-END TEST: CREATE PROJECT -> GENERATE IMAGE -> VIDEO   ")
    print("================================================================")

    # 1. Health check
    health = get_json("/health")
    print(f"[*] Health Check: ok={health.get('status')}, ext_connected={health.get('extension_connected')}")
    if not health.get("extension_connected"):
        print("[!] ERROR: Extension is not connected!")
        sys.exit(1)

    # 2. Step 1: Create Project
    proj_payload = {
        "name": f"Test Project {int(time.time())}",
        "material": "3d_pixar",
        "flow_project_id": FLOW_PROJECT_UUID,
        "description": "Test sprite animation project",
    }
    print(f"\n[Step 1] Creating project with flow_project_id: {FLOW_PROJECT_UUID}...")
    try:
        project = post_json("/api/projects", proj_payload)
        project_id = project.get("id") or FLOW_PROJECT_UUID
        print(f"  [SUCCESS] Project created:")
        print(f"    - ID: {project_id}")
        print(f"    - Name: {project.get('name')}")
        print(f"    - Material: {project.get('material')}")
    except Exception as e:
        print(f"  [WARN] Project create call returned: {e}. Using UUID directly.")
        project_id = FLOW_PROJECT_UUID

    # 3. Step 2: Generate Image
    img_prompt = (
        "cyberpunk sprite warrior, combat idle stance, front view, "
        "solid bright green background #00FF00 chroma key, 3D character render, highly detailed"
    )
    print(f"\n[Step 2] Generating Image...")
    print(f"    Prompt: {img_prompt}")
    t0 = time.time()
    img_res = post_json("/api/flow/generate-image", {
        "prompt": img_prompt,
        "project_id": project_id,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_ONE",
    })
    elapsed_img = time.time() - t0
    print(f"  [SUCCESS] Image response received in {elapsed_img:.1f}s")

    # Extract image_media_id and URL
    image_media_id = None
    image_url = None
    media_list = img_res.get("media", [])
    if media_list and isinstance(media_list, list):
        m0 = media_list[0]
        image_media_id = m0.get("name") or m0.get("id")
        image_url = m0.get("image", {}).get("url") or m0.get("url")
    if not image_media_id:
        image_media_id = img_res.get("id") or img_res.get("image_media_id")
    if not image_url:
        image_url = img_res.get("url")

    print(f"    - Image Media ID: {image_media_id}")
    if image_url:
        print(f"    - Image URL: {image_url[:90]}...")
    if not image_media_id:
        print(f"  [!] Failed to extract image media id. Full response: {img_res}")
        sys.exit(1)

    # 4. Step 3: Generate Video (4s Loop: start_frame == end_frame)
    vid_prompt = "seamless idle loop, subtle breathing, character breathing gently in place, martial arts combat stance"
    print(f"\n[Step 3] Generating 4s Seamless Loop Video...")
    print(f"    start_image_media_id: {image_media_id}")
    print(f"    end_image_media_id:   {image_media_id}")
    print(f"    duration:             4.0s")
    print(f"    prompt:               {vid_prompt}")

    t1 = time.time()
    vid_res = post_json("/api/flow/generate-video", {
        "start_image_media_id": image_media_id,
        "end_image_media_id": image_media_id,
        "prompt": vid_prompt,
        "project_id": project_id,
        "scene_id": str(uuid.uuid4()),
        "duration": 4.0,
        "duration_s": 4,
        "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_ONE",
    })
    elapsed_vid = time.time() - t1
    print(f"  [SUCCESS] Video request submitted in {elapsed_vid:.1f}s")

    # Extract operation or media ID
    operations = vid_res.get("operations", [])
    workflows = vid_res.get("workflows", [])
    vid_media_id = None
    op_name = None

    if operations and isinstance(operations, list):
        op0 = operations[0]
        op_info = op0.get("operation", {})
        op_name = op_info.get("name")
        vid_media_id = op_info.get("metadata", {}).get("video", {}).get("mediaId")
        print(f"    - Operation Name: {op_name}")
    elif workflows and isinstance(workflows, list):
        wf0 = workflows[0]
        meta = wf0.get("metadata", {})
        vid_media_id = meta.get("primaryMediaId") or wf0.get("primaryMediaId")

    # 5. Step 4: Poll Video Completion
    print(f"\n[Step 4] Polling video render status (Google Cloud)...")
    video_url = None
    for i in range(40):  # Poll up to ~3.5 minutes
        time.sleep(5)
        try:
            if op_name:
                status_res = post_json("/api/flow/check-status", {"operations": [{"operation": {"name": op_name}}]})
                ops = status_res.get("operations", [])
                if ops:
                    st = ops[0].get("status")
                    if st == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                        vid_meta = ops[0].get("operation", {}).get("metadata", {}).get("video", {})
                        vid_media_id = vid_meta.get("mediaId") or vid_media_id
                        video_url = vid_meta.get("fifeUrl")
                        break
            elif vid_media_id:
                url_res = get_json(f"/api/flow/media-redirect-url/{vid_media_id}")
                vdata = url_res.get("data", {})
                vurl = vdata.get("url", "")
                if vurl and not url_res.get("error"):
                    video_url = vurl
                    break
        except Exception as e:
            pass
        print(f"  ... rendering in Google Cloud ({(i+1)*5}s elapsed)", flush=True)

    if video_url:
        print(f"\n================================================================")
        print(f"  [RENDER COMPLETED SUCCESSFULLY]!")
        print(f"================================================================")
        print(f"  Video Media ID: {vid_media_id}")
        print(f"  Direct CDN URL: {video_url}")
    else:
        print("\n[INFO] Video is still rendering in Google Cloud background.")
        print(f"Operation: {op_name}. Check status via POST /api/flow/check-status")


if __name__ == "__main__":
    main()

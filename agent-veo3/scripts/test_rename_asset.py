"""Test Asset Rename API on Google Flow via mYWVGd RPC."""
import json
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://127.0.0.1:8100"
PROJECT_ID = "03e50309-8cab-4182-aa31-ee90b6f3e4be"
IMAGE_ASSET_ID = "9caf665b-72ea-44e4-b83a-02026d716e26"
VIDEO_ASSET_ID = "237af4c1-cfc6-42b4-8b93-73137b7443b4"


def post_json(endpoint: str, data: dict, timeout: int = 30) -> dict:
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


def get_json(endpoint: str, timeout: int = 15) -> dict:
    url = f"{API_BASE}{endpoint}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("================================================================")
    print("   TESTING GOOGLE FLOW BATCHEXECUTE: mYWVGd (ASSET RENAME)      ")
    print("================================================================")

    # 1. Health check
    health = get_json("/health")
    print(f"[*] Health Check: ok={health.get('status')}, ext={health.get('extension_connected')}")
    if not health.get("extension_connected"):
        print("[!] ERROR: Extension is not connected!")
        sys.exit(1)

    # 2. Test Rename Image via /api/flow/image/rename
    img_new_name = f"Warrior Idle Hero - {int(time.time()) % 1000}"
    print(f"\n[1] Renaming IMAGE ({IMAGE_ASSET_ID}) to '{img_new_name}'...")
    t0 = time.time()
    try:
        res_img = post_json("/api/flow/image/rename", {
            "asset_id": IMAGE_ASSET_ID,
            "title": img_new_name,
            "project_id": PROJECT_ID,
        })
        elapsed_img = time.time() - t0
        print(f"  [SUCCESS] Image renamed in {elapsed_img:.2f}s:")
        print(f"    - Asset ID: {res_img.get('assetId')}")
        print(f"    - Display Name: {res_img.get('displayName')}")
        print(f"    - Media ID: {res_img.get('mediaId')}")
        print(f"    - Project ID: {res_img.get('projectId')}")
    except Exception as e:
        print(f"  [FAILED] Image rename failed: {e}")

    # 3. Test Rename Video via /api/flow/video/rename
    vid_new_name = f"Combat Stance 4s Loop - {int(time.time()) % 1000}"
    print(f"\n[2] Renaming VIDEO ({VIDEO_ASSET_ID}) to '{vid_new_name}'...")
    t1 = time.time()
    try:
        res_vid = post_json("/api/flow/video/rename", {
            "asset_id": VIDEO_ASSET_ID,
            "name": vid_new_name,
            "project_id": PROJECT_ID,
        })
        elapsed_vid = time.time() - t1
        print(f"  [SUCCESS] Video renamed in {elapsed_vid:.2f}s:")
        print(f"    - Asset ID: {res_vid.get('assetId')}")
        print(f"    - Display Name: {res_vid.get('displayName')}")
        print(f"    - Media ID: {res_vid.get('mediaId')}")
        print(f"    - Project ID: {res_vid.get('projectId')}")
    except Exception as e:
        print(f"  [FAILED] Video rename failed: {e}")

    print("\n================================================================")
    print("   TEST COMPLETED                                               ")
    print("================================================================")


if __name__ == "__main__":
    main()

"""Generate images via Flow API and download to output folder.
Handles timeouts gracefully, tries each image independently.
"""
import json
import os
import time
import urllib.request

BASE = "http://127.0.0.1:8100"
PID = "c5ece4c3-7db1-4230-b314-6a96f4348667"
OUT = r"D:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\output"
os.makedirs(OUT, exist_ok=True)


def api(path, body, timeout=300):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return 200, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"raw": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def download_image(url, filename):
    filepath = os.path.join(OUT, filename)
    try:
        urllib.request.urlretrieve(url, filepath)
        size_kb = os.path.getsize(filepath) / 1024
        print(f"  Downloaded: {filename} ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False


IMAGES = [
    {
        "name": "landscape_sunset",
        "prompt": "A breathtaking golden sunset over calm ocean waves, dramatic clouds in orange and purple, lighthouse silhouette on rocky cliff, photorealistic 4K",
        "aspect": "IMAGE_ASPECT_RATIO_LANDSCAPE",
    },
    {
        "name": "portrait_warrior",
        "prompt": "A fierce samurai warrior in traditional black armor standing in a bamboo forest, cherry blossom petals falling, dramatic rim lighting, photorealistic",
        "aspect": "IMAGE_ASPECT_RATIO_PORTRAIT",
    },
]


def main():
    print("=" * 60)
    print("  TAO ANH QUA FLOW API & TAI VE OUTPUT")
    print(f"  Timeout: 300s | Project: {PID[:12]}...")
    print("=" * 60)

    results = []
    for i, img in enumerate(IMAGES, 1):
        orient = img["aspect"].split("_")[-1].lower()
        print(f"\n[{i}/{len(IMAGES)}] {img['name']} ({orient})")
        print(f"  Prompt: {img['prompt'][:60]}...")

        s, data = api("/flow/generate-image", {
            "prompt": img["prompt"],
            "project_id": PID,
            "aspect_ratio": img["aspect"],
            "user_paygate_tier": "PAYGATE_TIER_TWO",
        }, timeout=300)

        if s == 0:
            print(f"  TIMEOUT/ERROR: {data.get('error', '?')}")
            results.append({"name": img["name"], "ok": False, "error": "timeout"})
        elif s == 200:
            media = data.get("media", [])
            if media:
                gen_img = media[0].get("image", {}).get("generatedImage", {})
                media_id = gen_img.get("mediaId", "")
                fife_url = gen_img.get("fifeUrl", "")
                print(f"  Media ID: {media_id}")
                if fife_url:
                    filename = f"{img['name']}_{media_id[:8]}.jpg"
                    ok = download_image(fife_url, filename)
                    results.append({"name": img["name"], "media_id": media_id, "file": filename, "ok": ok})
                else:
                    print("  No fifeUrl, trying mediaUrl...")
                    media_url = gen_img.get("mediaUrl", "")
                    if media_url:
                        filename = f"{img['name']}_{media_id[:8]}.jpg"
                        ok = download_image(media_url, filename)
                        results.append({"name": img["name"], "media_id": media_id, "file": filename, "ok": ok})
                    else:
                        print(f"  Full response keys: {list(gen_img.keys())}")
                        print(f"  Raw: {json.dumps(gen_img, ensure_ascii=False)[:500]}")
                        results.append({"name": img["name"], "media_id": media_id, "ok": False})
            else:
                print(f"  No media. Response: {json.dumps(data, ensure_ascii=False)[:300]}")
                results.append({"name": img["name"], "ok": False})
        else:
            detail = data.get("detail", str(data)[:200])
            print(f"  ERROR {s}: {detail}")
            results.append({"name": img["name"], "ok": False, "error": detail})

        if i < len(IMAGES):
            print("  Waiting 8s...")
            time.sleep(8)

    print("\n" + "=" * 60)
    print("  KET QUA")
    print("=" * 60)
    for r in results:
        icon = "OK" if r.get("ok") else "FAIL"
        info = r.get("file", r.get("error", "?"))
        print(f"  [{icon}] {r['name']}: {info}")
    print(f"\n  Output: {OUT}")


if __name__ == "__main__":
    main()

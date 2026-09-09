"""Test R2V x2 + F2F x2 with existing images."""
import json
import time
import urllib.request

PID = "c5ece4c3-7db1-4230-b314-6a96f4348667"
IMG1 = "dffaaffc-144b-441f-8179-36e462cf62fd"
IMG2 = "33119369-12a0-47d4-9662-bad32edad6e1"


def api(method, path, body=None):
    url = f"http://127.0.0.1:8100{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def get_ops(result):
    data = result.get("data", result)
    return data.get("operations", [])


print("=" * 60)
print("  TEST R2V x2 + F2F x2 (8s, landscape)")
print("=" * 60)

# --- R2V x2 ---
print("\n[1/2] R2V: Video tu anh tham chieu, x2, 8s")
print(f"  Ref image: {IMG1[:12]}...")
s, r = api("POST", "/flow/generate-video-refs", {
    "reference_media_ids": [IMG1],
    "prompt": "A golden retriever puppy playfully chasing butterflies in a garden, warm cinematic lighting, slow motion camera tracking",
    "project_id": PID,
    "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "user_paygate_tier": "PAYGATE_TIER_TWO",
    "count": 2,
})
print(f"  Status: {s}")
if s == 200:
    ops = get_ops(r)
    print(f"  Operations: {len(ops)}")
    for op in ops:
        name = op.get("operation", {}).get("name", "?")
        print(f"    -> {name}")
    print("  R2V OK!")
else:
    print(f"  LOI: {json.dumps(r, ensure_ascii=False)[:300]}")

time.sleep(5)

# --- F2F x2 ---
print("\n[2/2] F2F: Noi frame video, x2, 8s")
print(f"  Start: {IMG1[:12]}...")
print(f"  End:   {IMG2[:12]}...")
s2, r2 = api("POST", "/flow/generate-video", {
    "start_image_media_id": IMG1,
    "end_image_media_id": IMG2,
    "prompt": "The puppy smoothly transitions from sitting to running, camera follows action, cinematic slow motion",
    "project_id": PID,
    "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "duration": 8, "duration_s": 8,
    "model_family": "veo",
    "user_paygate_tier": "PAYGATE_TIER_TWO",
    "count": 2,
})
print(f"  Status: {s2}")
if s2 == 200:
    ops2 = get_ops(r2)
    print(f"  Operations: {len(ops2)}")
    for op in ops2:
        name = op.get("operation", {}).get("name", "?")
        print(f"    -> {name}")
    print("  F2F OK!")
else:
    print(f"  LOI: {json.dumps(r2, ensure_ascii=False)[:300]}")

print("\n" + "=" * 60)
print("  KET QUA")
print("=" * 60)
print(f"  R2V x2 8s: {'OK' if s == 200 else 'LOI'}")
print(f"  F2F x2 8s: {'OK' if s2 == 200 else 'LOI'}")

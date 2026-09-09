"""Test Omni Flash video generation via API /api/flow/generate-video."""
import json
import urllib.request
import time

URL = "http://127.0.0.1:8100/api/flow/generate-video"
PROJECT_ID = "03e50309-8cab-4182-aa31-ee90b6f3e4be"

payload = {
    "prompt": "cute anime mascot robot smiling, green background #00FF00",
    "project_id": PROJECT_ID,
    "model_family": "omni_flash",
    "duration_s": 4,
    "quality": "720p",
    "count": 1,
    "title": "[đứng yên - 0] Robot Omni - 01",
}

print(f"Submitting Omni Flash generation to {URL}...")
req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        data = json.loads(body)
        print("Success! Response:")
        print(json.dumps(data, indent=2))
except urllib.error.HTTPError as err:
    print(f"HTTP Error {err.code}: {err.reason}")
    print(err.read().decode("utf-8", errors="ignore"))
except Exception as e:
    print("Error:", e)

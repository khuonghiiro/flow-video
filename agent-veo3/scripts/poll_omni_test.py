"""Poll status for recently generated Omni video."""
import asyncio
import json
import urllib.request
import time

MEDIA_ID = "12218138-7121-4bf9-8ddf-10fbc6884094"
URL = f"http://127.0.0.1:8100/api/flow/media-redirect-url/{MEDIA_ID}"

print(f"Polling media URL for {MEDIA_ID} at {URL}...")
for i in range(12):
    try:
        req = urllib.request.Request(URL)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[{i+1}/12] Result:", json.dumps(data, indent=2))
            if data.get("data", {}).get("video") or data.get("data", {}).get("video_url"):
                print("Video completed successfully!")
                break
    except Exception as e:
        print(f"[{i+1}/12] Waiting... ({e})")
    time.sleep(5)

import asyncio
import aiohttp
import json
import time
from pathlib import Path

API_BASE = "http://127.0.0.1:8100"
PROJECT_ID = "0e81ddf8-19b2-40f0-9071-41d62e34b5f3"
IMAGE_PATH = Path(r"d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\output\cyberpunk_city_1788946909_cleaned.jpeg")

async def test_upload():
    print(f"Testing upload of {IMAGE_PATH} to project {PROJECT_ID}...")
    if not IMAGE_PATH.exists():
        print(f"File does not exist: {IMAGE_PATH}")
        return

    url = f"{API_BASE}/api/flow/upload-image"
    payload = {
        "file_path": str(IMAGE_PATH),
        "project_id": PROJECT_ID,
        "file_name": IMAGE_PATH.name
    }

    t0 = time.time()
    # Use 180s timeout
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=180) as resp:
                print(f"Status: {resp.status}")
                text = await resp.text()
                elapsed = time.time() - t0
                print(f"Elapsed: {elapsed:.2f}s")
                print(f"Response: {text}")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"Failed after {elapsed:.2f}s with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_upload())

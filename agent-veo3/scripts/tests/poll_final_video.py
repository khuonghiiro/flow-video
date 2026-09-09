import os
import sys
import time
import json
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://127.0.0.1:8100"
PROJECT_ID = "0e81ddf8-19b2-40f0-9071-41d62e34b5f3"
OPERATION_ID = "9f83fe51-19f2-4ae9-9002-8ddb5803396a"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"

def poll_and_download():
    print(f"[*] Theo dõi tiến độ sinh video Operation: {OPERATION_ID}...", flush=True)
    url_poll = f"{API_BASE}/api/flow/check-status"
    payload = json.dumps({
        "operations": [{"operation": {"name": OPERATION_ID}}],
        "project_id": PROJECT_ID
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    
    start_time = time.time()
    for attempt in range(1, 40):  # max ~6-7 mins
        time.sleep(10)
        try:
            req = urllib.request.Request(url_poll, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            
            ops = res.get("operations", [])
            if not ops:
                print(f"  [{attempt}] Chưa có phản hồi operation.", flush=True)
                continue
                
            entry = ops[0]
            status = entry.get("status")
            elapsed = time.time() - start_time
            print(f"  [{attempt}] (+{elapsed:.0f}s) Status: {status}", flush=True)
            
            if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                meta_video = (entry.get("operation", {}).get("metadata", {}).get("video", {}))
                video_url = meta_video.get("fifeUrl") or meta_video.get("url")
                media_id = meta_video.get("mediaId", "video")
                print(f"\n[THÀNH CÔNG] Video đã sẵn sàng tải về!", flush=True)
                print(f"  Media ID: {media_id}", flush=True)
                print(f"  Video URL: {video_url}", flush=True)
                
                if video_url:
                    dest_file = OUTPUT_DIR / f"cyberpunk_veo_{media_id[:8]}.mp4"
                    print(f"  Đang tải video về: {dest_file.name}...", flush=True)
                    urllib.request.urlretrieve(video_url, str(dest_file))
                    print(f"  [XONG] File video đã lưu: {dest_file} ({dest_file.stat().st_size / (1024*1024):.2f} MB)", flush=True)
                return True
                
            elif status == "MEDIA_GENERATION_STATUS_FAILED":
                err = entry.get("error") or entry.get("operation", {}).get("error")
                print(f"\n[LỖI] Video sinh thất bại: {err}", flush=True)
                return False
                
        except Exception as e:
            print(f"  [{attempt}] Lỗi poll: {e}", flush=True)

    print("\n[HẾT THỜI GIAN] Video vẫn đang tiếp tục render trên Google Flow.", flush=True)
    return False

if __name__ == "__main__":
    poll_and_download()

"""Movie Keyframe Chaining Pipeline (8s Start-End Frame Interpolation).
Implements the 4-candidate selection loop and sequential frame-to-frame video generation.
Adheres to:
- plans/plan_movie_pipeline.md
- AI Workspace Directives (UTF-8, Auto-rename, Modularity)
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Dict, List, Optional
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_DIR = SCRIPT_DIR.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("movie_chain")

API_BASE = "http://127.0.0.1:8100/api"
OUTPUT_BASE = AGENT_DIR / "output" / "movies"


def get_movie_dir(movie_slug: str) -> Path:
    mdir = OUTPUT_BASE / movie_slug
    (mdir / "keyframes").mkdir(parents=True, exist_ok=True)
    (mdir / "candidates").mkdir(parents=True, exist_ok=True)
    (mdir / "clips").mkdir(parents=True, exist_ok=True)
    (mdir / "final").mkdir(parents=True, exist_ok=True)
    return mdir


def load_movie_meta(movie_dir: Path) -> dict:
    meta_path = movie_dir / "movie_meta.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "title": movie_dir.name,
        "project_id": "",
        "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
        "video_aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "keyframes": [],
        "clips": [],
    }


def save_movie_meta(movie_dir: Path, meta: dict):
    meta_path = movie_dir / "movie_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def download_file(url: str, dest_path: Path) -> bool:
    try:
        resp = requests.get(url, timeout=90)
        if resp.status_code == 200:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(resp.content)
            return True
        logger.warning("Download failed (%d): %s", resp.status_code, url[:80])
    except Exception as e:
        logger.error("Download error for %s: %s", url[:80], e)
    return False


def generate_single_image_candidate(
    project_id: str,
    prompt: str,
    cand_idx: int,
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
    character_media_ids: Optional[List[str]] = None,
) -> dict:
    """Generate 1 candidate image via Flow API with retries."""
    url = f"{API_BASE}/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": project_id,
        "aspect_ratio": aspect_ratio,
        "user_paygate_tier": "PAYGATE_TIER_TWO",
    }
    if character_media_ids:
        body["character_media_ids"] = character_media_ids

    logger.info("Submitting Candidate #%d...", cand_idx)
    for attempt in range(5):
        try:
            resp = requests.post(url, json=body, timeout=120)
            data = resp.json()
            if resp.status_code == 200:
                break
            if "Extension not connected" in str(data):
                logger.warning("Extension reconnecting, waiting 3s (attempt %d/5)...", attempt + 1)
                time.sleep(3)
                continue
            logger.error("Candidate #%d error (HTTP %d): %s", cand_idx, resp.status_code, data)
            return {"candidate": cand_idx, "error": data}
        except Exception as e:
            logger.warning("Candidate #%d exception: %s (retrying...)", cand_idx, e)
            time.sleep(2)
    else:
        return {"candidate": cand_idx, "error": "Max retries exceeded"}

    media_list = data.get("media", [])
    if not media_list and isinstance(data.get("data"), dict):
        media_list = data["data"].get("media", [])

    if media_list:
        m = media_list[0]
        mid = m.get("name")
        img_block = m.get("image", {}) if isinstance(m.get("image"), dict) else {}
        gen_img = img_block.get("generatedImage", {}) if isinstance(img_block.get("generatedImage"), dict) else {}
        fife_url = gen_img.get("fifeUrl") or img_block.get("fifeUrl") or m.get("fifeUrl")
        return {
            "candidate": cand_idx,
            "media_id": mid,
            "url": fife_url,
            "raw": m,
        }
    return {"candidate": cand_idx, "error": "No media returned"}


def generate_candidate_batch(
    movie_slug: str,
    project_id: str,
    frame_index: int,
    prompt: str,
    aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE",
    character_media_ids: Optional[List[str]] = None,
    count: int = 4,
    batch_attempt: int = 1,
) -> List[dict]:
    """Generate 4 candidate images in parallel for frame N."""
    movie_dir = get_movie_dir(movie_slug)
    cand_dir = movie_dir / "candidates"

    logger.info("=== GENERATING BATCH OF %d CANDIDATES (Frame %d, Batch #%d) ===", count, frame_index, batch_attempt)
    logger.info("Refs: %s", character_media_ids or "None")

    def _worker(cand_num: int):
        if cand_num > 1:
            time.sleep((cand_num - 1) * 1.5)
        return generate_single_image_candidate(
            project_id,
            prompt,
            cand_num,
            aspect_ratio,
            character_media_ids,
        )

    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(_worker, i + 1) for i in range(count)]
        results = [f.result() for f in futures]

    saved = []
    for res in results:
        idx = res.get("candidate")
        url = res.get("url")
        mid = res.get("media_id")
        if url and mid:
            local_name = f"frame_{frame_index:02d}_batch{batch_attempt}_cand{idx}.png"
            local_path = cand_dir / local_name
            if download_file(url, local_path):
                saved.append({
                    "candidate": idx,
                    "frame_index": frame_index,
                    "batch_attempt": batch_attempt,
                    "media_id": mid,
                    "url": url,
                    "local_path": str(local_path),
                })
        else:
            logger.warning("Candidate #%d did not return valid image", idx)

    batch_meta_file = cand_dir / f"candidates_frame_{frame_index:02d}_batch{batch_attempt}.json"
    batch_meta_file.write_text(json.dumps(saved, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 65)
    print(f"🎬 [Movie: {movie_slug}] Frame {frame_index} Candidates ({len(saved)}/{count}):")
    for s in saved:
        print(f"  👉 Candidate #{s['candidate']}: {s['media_id'][:12]}... | Path: {s['local_path']}")
    print("=" * 65 + "\n")
    return saved


def upload_frame_reference(project_id: str, local_path: Path, file_name: str) -> Optional[str]:
    """Upload local keyframe to Flow project as an official reference asset."""
    url = f"{API_BASE}/flow/upload-image"
    payload = {
        "file_path": str(local_path),
        "project_id": project_id,
        "file_name": file_name,
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            mid = resp.json().get("media_id")
            logger.info("Uploaded reference asset %s -> media_id: %s", file_name, mid)
            return mid
        logger.warning("Upload reference returned %d: %s", resp.status_code, resp.text[:100])
    except Exception as e:
        logger.error("Upload reference error: %s", e)
    return None


def pick_and_confirm_frame(
    movie_slug: str,
    frame_index: int,
    chosen_candidate: dict,
    prompt: str,
) -> dict:
    """Save selected candidate as the official keyframe and upload as project reference."""
    movie_dir = get_movie_dir(movie_slug)
    meta = load_movie_meta(movie_dir)

    target_name = f"frame_{frame_index:02d}.png"
    target_path = movie_dir / "keyframes" / target_name
    shutil.copy2(chosen_candidate["local_path"], target_path)

    pid = meta.get("project_id", "")
    ref_mid = None
    if pid:
        ref_mid = upload_frame_reference(pid, target_path, f"frame_{frame_index:02d}_ref.png")

    frame_entry = {
        "index": frame_index,
        "media_id": chosen_candidate["media_id"],
        "ref_media_id": ref_mid or chosen_candidate["media_id"],
        "prompt": prompt,
        "local_path": str(target_path),
        "url": chosen_candidate.get("url", ""),
        "timestamp_sec": (frame_index - 1) * 8,
    }

    # Update or append in meta
    existing = [f for f in meta["keyframes"] if f.get("index") == frame_index]
    if existing:
        idx = meta["keyframes"].index(existing[0])
        meta["keyframes"][idx] = frame_entry
    else:
        meta["keyframes"].append(frame_entry)

    save_movie_meta(movie_dir, meta)
    logger.info(
        "✅ Confirmed Frame %d: gen_id=%s, ref_id=%s -> %s",
        frame_index,
        chosen_candidate["media_id"][:12],
        frame_entry["ref_media_id"][:12],
        target_path,
    )
    return frame_entry


def render_transition_video_8s(
    movie_slug: str,
    project_id: str,
    start_frame_idx: int,
    end_frame_idx: int,
    transition_prompt: str,
    aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE",
) -> dict:
    """Render 8-second start_end_frame video between frame N and frame N+1."""
    movie_dir = get_movie_dir(movie_slug)
    meta = load_movie_meta(movie_dir)

    # Lookup start & end keyframes
    kf_map = {f["index"]: f for f in meta.get("keyframes", [])}
    if start_frame_idx not in kf_map or end_frame_idx not in kf_map:
        raise ValueError(f"Missing keyframe: need {start_frame_idx} and {end_frame_idx}")

    start_mid = kf_map[start_frame_idx]["media_id"]
    end_mid = kf_map[end_frame_idx]["media_id"]

    clip_num = start_frame_idx
    logger.info(
        "🎬 Rendering Video Clip #%02d (8s): Frame %d (%s) -> Frame %d (%s)...",
        clip_num, start_frame_idx, start_mid[:8], end_frame_idx, end_mid[:8]
    )

    url = f"{API_BASE}/flow/generate-video"
    body = {
        "prompt": transition_prompt,
        "project_id": project_id,
        "start_image_media_id": start_mid,
        "end_image_media_id": end_mid,
        "duration": 8,
        "aspect_ratio": aspect_ratio,
        "user_paygate_tier": "PAYGATE_TIER_TWO",
    }

    resp = requests.post(url, json=body, timeout=120)
    data = resp.json()
    if resp.status_code != 200:
        logger.error("Video submission error: %s", data)
        return {"error": data}

    op_id = None
    ops = data.get("operations") or (data.get("data", {}).get("operations", []) if isinstance(data.get("data"), dict) else [])
    if ops and isinstance(ops, list):
        first_op = ops[0]
        if isinstance(first_op, dict):
            inner_op = first_op.get("operation", {})
            op_id = inner_op.get("name") if isinstance(inner_op, dict) else None
            if not op_id:
                op_id = first_op.get("name") or first_op.get("operationId")
    if not op_id:
        op_id = data.get("operation_id") or data.get("name")

    clip_entry = {
        "clip_index": clip_num,
        "start_frame": start_frame_idx,
        "end_frame": end_frame_idx,
        "operation_id": op_id,
        "start_media_id": start_mid,
        "end_media_id": end_mid,
        "prompt": transition_prompt,
        "duration": 8,
        "status": "GENERATING",
    }

    meta["clips"].append(clip_entry)
    save_movie_meta(movie_dir, meta)
    logger.info("Submitted Video Clip #%02d with OpID: %s", clip_num, op_id)
    return clip_entry


def get_auto_refs_for_frame(movie_dir: Path, target_frame_idx: int) -> List[str]:
    """Auto-resolve identity and state anchors:
    - Frame 1: []
    - Frame 2: [Frame 1]
    - Frame 3+: [Frame 1 (Identity anchor), Frame {target - 1} (State/momentum anchor)]
    """
    meta = load_movie_meta(movie_dir)
    kf_map = {f["index"]: (f.get("ref_media_id") or f["media_id"]) for f in meta.get("keyframes", [])}
    if target_frame_idx <= 1:
        return []
    if target_frame_idx == 2:
        return [kf_map[1]] if 1 in kf_map else []
    
    refs = []
    if 1 in kf_map:
        refs.append(kf_map[1])
    prev_idx = target_frame_idx - 1
    if prev_idx in kf_map:
        refs.append(kf_map[prev_idx])
    return refs


def print_movie_status(movie_slug: str):
    movie_dir = get_movie_dir(movie_slug)
    meta = load_movie_meta(movie_dir)
    print("\n" + "=" * 70)
    print(f"🎬 MOVIE STATUS: {movie_slug.upper()} (Project ID: {meta.get('project_id') or 'N/A'})")
    print("-" * 70)
    print("📌 KEYFRAMES:")
    if not meta.get("keyframes"):
        print("   (Chưa có keyframe nào được chọn)")
    else:
        for kf in meta["keyframes"]:
            print(f"   [Frame {kf['index']:02d}] ({kf['timestamp_sec']}s) | Media ID: {kf['media_id'][:12]}... | File: {kf['local_path']}")
    
    print("-" * 70)
    print("🎥 CLIPS (8s Start-End Frame):")
    if not meta.get("clips"):
        print("   (Chưa có clip video nào được render)")
    else:
        for c in meta["clips"]:
            print(f"   [Clip {c['clip_index']:02d}] Frame {c['start_frame']} -> Frame {c['end_frame']} | Op: {c.get('operation_id')} | Status: {c.get('status')}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Movie Keyframe Chaining Pipeline (8s)")
    parser.add_argument("--movie", required=True, help="Movie slug (e.g. dai-chien-hac-phong)")
    parser.add_argument("--project-id", default="", help="Google Flow Project ID")
    parser.add_argument("--status", action="store_true", help="Print current status of keyframes & clips")
    parser.add_argument("--step", choices=["candidate", "pick", "video"], help="Action step")
    parser.add_argument("--frame", type=int, default=1, help="Target frame index (1, 2, 3...)")
    parser.add_argument("--candidate", type=int, default=1, help="Chosen candidate index (1..4) for pick step")
    parser.add_argument("--batch-attempt", type=int, default=1, help="Batch attempt counter")
    parser.add_argument("--prompt", default="", help="Prompt for image or video transition")
    parser.add_argument("--aspect", default="IMAGE_ASPECT_RATIO_LANDSCAPE", help="Aspect ratio for candidate images")
    parser.add_argument("--video-aspect", default="VIDEO_ASPECT_RATIO_LANDSCAPE", help="Aspect ratio for 8s video")
    parser.add_argument("--start-frame", type=int, default=1, help="Start frame index for video")
    parser.add_argument("--end-frame", type=int, default=2, help="End frame index for video")
    args = parser.parse_args()

    movie_dir = get_movie_dir(args.movie)
    meta = load_movie_meta(movie_dir)
    if args.project_id:
        meta["project_id"] = args.project_id
        save_movie_meta(movie_dir, meta)
    pid = meta.get("project_id") or args.project_id

    if args.status:
        print_movie_status(args.movie)
        sys.exit(0)

    if args.step == "candidate":
        if not pid:
            print("❌ Lỗi: Cần cung cấp --project-id")
            sys.exit(1)
        if not args.prompt:
            print("❌ Lỗi: Cần cung cấp --prompt cho Frame")
            sys.exit(1)
        refs = get_auto_refs_for_frame(movie_dir, args.frame)
        generate_candidate_batch(
            movie_slug=args.movie,
            project_id=pid,
            frame_index=args.frame,
            prompt=args.prompt,
            aspect_ratio=args.aspect,
            character_media_ids=refs,
            count=4,
            batch_attempt=args.batch_attempt,
        )

    elif args.step == "pick":
        cand_dir = movie_dir / "candidates"
        batch_meta_file = cand_dir / f"candidates_frame_{args.frame:02d}_batch{args.batch_attempt}.json"
        
        chosen = None
        if batch_meta_file.exists():
            try:
                candidates_list = json.loads(batch_meta_file.read_text(encoding="utf-8"))
                for c in candidates_list:
                    if c.get("candidate") == args.candidate:
                        chosen = c
                        break
            except Exception as e:
                logger.warning("Could not read batch meta json: %s", e)

        if not chosen:
            matched_file = cand_dir / f"frame_{args.frame:02d}_batch{args.batch_attempt}_cand{args.candidate}.png"
            if not matched_file.exists():
                print(f"❌ Không tìm thấy candidate file: {matched_file}")
                sys.exit(1)
            chosen = {
                "candidate": args.candidate,
                "media_id": f"media_f{args.frame}_c{args.candidate}",
                "local_path": str(matched_file),
            }

        print(f"Confirming Candidate #{args.candidate} for Frame {args.frame} (media_id: {chosen.get('media_id')})...")
        pick_and_confirm_frame(
            movie_slug=args.movie,
            frame_index=args.frame,
            chosen_candidate=chosen,
            prompt=args.prompt,
        )
        print_movie_status(args.movie)

    elif args.step == "video":
        if not pid:
            print("❌ Lỗi: Cần cung cấp --project-id")
            sys.exit(1)
        if not args.prompt:
            print("❌ Lỗi: Cần cung cấp --prompt chuyển động 8s")
            sys.exit(1)
        render_transition_video_8s(
            movie_slug=args.movie,
            project_id=pid,
            start_frame_idx=args.start_frame,
            end_frame_idx=args.end_frame,
            transition_prompt=args.prompt,
            aspect_ratio=args.video_aspect,
        )
        print_movie_status(args.movie)


"""Script to generate a batch of candidate images in parallel for character angles.
Adheres to plan_character_pipeline.md:
- Batch 3 candidates for angle 0°
- Saves candidates locally in agent-veo3/output/<char_key>/
"""

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
import sys
from pathlib import Path
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

from agent.services.prompt_templates import ANGLE_PROMPT_TEMPLATES, format_template

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("candidate_batch")

API_BASE = "http://127.0.0.1:8100/api"
OUTPUT_BASE = AGENT_DIR / "output"


def download_image(url: str, dest_path: Path) -> bool:
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(resp.content)
            logger.info("Saved image (%d bytes) to %s", len(resp.content), dest_path)
            return True
        logger.warning("Download failed with HTTP %d: %s", resp.status_code, url[:80])
    except Exception as e:
        logger.error("Download error for %s: %s", url[:80], e)
    return False


def generate_single_candidate(project_id: str, prompt: str, candidate_idx: int, character_media_ids: list = None) -> dict:
    url = f"{API_BASE}/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": project_id,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
    }
    if character_media_ids:
        body["character_media_ids"] = character_media_ids

    logger.info("Submitting Candidate #%d...", candidate_idx)
    for attempt in range(5):
        try:
            resp = requests.post(url, json=body, timeout=120)
            data = resp.json()
            if resp.status_code == 200:
                break
            if "Extension not connected" in str(data):
                logger.warning("Extension reconnecting, waiting 3s (attempt %d/5)...", attempt + 1)
                import time
                time.sleep(3)
                continue
            logger.error("Candidate #%d error (HTTP %d): %s", candidate_idx, resp.status_code, data)
            return {"candidate": candidate_idx, "error": data}
        except Exception as e:
            logger.exception("Candidate #%d exception: %s", candidate_idx, e)
            import time
            time.sleep(2)
    else:
        logger.error("Candidate #%d failed after retries", candidate_idx)
        return {"candidate": candidate_idx, "error": "Extension reconnection timeout"}

    media_list = data.get("media", [])
    if not media_list and isinstance(data.get("data"), dict):
        media_list = data["data"].get("media", [])

    if media_list:
        m = media_list[0]
        mid = m.get("name")
        img_block = m.get("image", {}) if isinstance(m.get("image"), dict) else {}
        gen_img = img_block.get("generatedImage", {}) if isinstance(img_block.get("generatedImage"), dict) else {}
        fife_url = gen_img.get("fifeUrl") or img_block.get("fifeUrl") or m.get("fifeUrl")
        logger.info("Candidate #%d generated: media_id=%s", candidate_idx, mid)
        return {
            "candidate": candidate_idx,
            "media_id": mid,
            "url": fife_url,
            "raw": m,
        }
    logger.warning("Candidate #%d returned no media items: %s", candidate_idx, data)
    return {"candidate": candidate_idx, "error": "No media returned", "raw": data}


def run_batch_0(character_key: str, project_id: str, customizer: dict, count: int = 3):
    char_dir = OUTPUT_BASE / character_key
    char_dir.mkdir(parents=True, exist_ok=True)

    raw_template = ANGLE_PROMPT_TEMPLATES["0"]
    prompt = format_template(raw_template, customizer)

    logger.info("=== GENERATING BATCH OF %d CANDIDATES FOR ANGLE 0° ===", count)
    logger.info("Character: %s | Project ID: %s", character_key, project_id)

    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = [
            executor.submit(generate_single_candidate, project_id, prompt, i + 1)
            for i in range(count)
        ]
        results = [f.result() for f in futures]

    # Download images
    saved_candidates = []
    for res in results:
        idx = res.get("candidate")
        url = res.get("url")
        mid = res.get("media_id")
        if url and mid:
            local_file = char_dir / f"candidate_0_{idx}.png"
            ok = download_image(url, local_file)
            if ok:
                saved_candidates.append({
                    "candidate": idx,
                    "media_id": mid,
                    "url": url,
                    "local_path": str(local_file),
                })
        else:
            logger.warning("Candidate #%d failed to produce valid image result", idx)

    meta_file = char_dir / "candidates_0.json"
    meta_file.write_text(json.dumps(saved_candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Candidate batch metadata saved to %s", meta_file)
    print("\n" + "=" * 60)
    print(f"Angle 0° Candidates Generated: {len(saved_candidates)}/{count}")
    for sc in saved_candidates:
        print(f" -> Candidate #{sc['candidate']}: media_id={sc['media_id']} | path={sc['local_path']}")
    print("=" * 60)
    return saved_candidates


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", default="so-tieu-dao")
    parser.add_argument("--project-id", default="f4262993-3551-4382-8d5f-328b2e10a6d4")
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()

    customizer = {
        "characterName": "Sở Tiêu Dao (Chu Xiaoyao)",
        "style": "2D Xianxia/Fantasy manhwa anime chibi sprite, bold clean linework, flat cel-shaded coloring, mature 4.8-5.0 heads ratio",
        "gender": "male",
        "age": "young adult (20-22)",
        "hairStyleColor": "Long silky natural black hair flowing loosely in soft rogue locks, loosely tied back at nape with a simple cloth ribbon, face-framing sidelocks draping past chin, natural fringe bangs",
        "outfitDescription": "Two-layer rogue martial artist daoist robe: inner layer unbleached ivory white cross-collar robe, outer layer muted slate-cyan and deep indigo linen robe with subtle cloudy patterns, layered wide cloth sash with a rustic braided rope belt tied simply at waist, flat cloth martial boots with zero heels",
        "primaryColor": "Muted Slate Cyan & Deep Indigo Linen",
        "accentColor": "Natural Flaxen Ivory & Charcoal Gray",
        "skinTone": "Fair warm ivory natural skin tone seamlessly matching neck and hands",
        "weaponType": "None (empty hands, pure martial arts)",
        "spellElement": "Tiêu dao thanh phong linh lực",
        "chromaBgHex": "#00FF00",
    }

    run_batch_0(args.character, args.project_id, customizer, args.count)

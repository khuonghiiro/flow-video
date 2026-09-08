"""Script to generate dual-ref angle candidates using Mannequin Pose Guide.
Adheres strictly to plan_character_pipeline.md.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
import sys
import time
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
logger = logging.getLogger("dualref_angle")

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


def generate_single_candidate(project_id: str, prompt: str, candidate_idx: int, character_media_ids: list) -> dict:
    url = f"{API_BASE}/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": project_id,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "character_media_ids": character_media_ids,
    }

    logger.info("Submitting Candidate #%d (refs=%s)...", candidate_idx, [m[:8] for m in character_media_ids])
    data = None
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
            logger.error("Candidate #%d error (HTTP %d): %s", candidate_idx, resp.status_code, data)
            return {"candidate": candidate_idx, "error": data}
        except Exception as e:
            logger.exception("Candidate #%d exception: %s", candidate_idx, e)
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


def run_angle_batch(character_key: str, project_id: str, angle: str, character_media_ids: list, customizer: dict, count: int = 2):
    char_dir = OUTPUT_BASE / character_key
    char_dir.mkdir(parents=True, exist_ok=True)

    raw_template = ANGLE_PROMPT_TEMPLATES[angle]
    prompt = format_template(raw_template, customizer)

    logger.info("=== GENERATING %d DUAL-REF CANDIDATES FOR ANGLE %s° ===", count, angle)
    logger.info("Character: %s | Project ID: %s", character_key, project_id)
    logger.info("References: %s", character_media_ids)

    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = [
            executor.submit(generate_single_candidate, project_id, prompt, i + 1, character_media_ids)
            for i in range(count)
        ]
        results = [f.result() for f in futures]

    saved_candidates = []
    for res in results:
        idx = res.get("candidate")
        url = res.get("url")
        mid = res.get("media_id")
        if url and mid:
            local_file = char_dir / f"candidate_{angle}_{idx}.png"
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

    meta_file = char_dir / f"candidates_{angle}.json"
    meta_file.write_text(json.dumps(saved_candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 60)
    print(f"Angle {angle}° Candidates Generated: {len(saved_candidates)}/{count}")
    for sc in saved_candidates:
        print(f" -> Candidate #{sc['candidate']}: media_id={sc['media_id']} | path={sc['local_path']}")
    print("=" * 60)
    return saved_candidates


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", required=True)
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--angle", required=True)
    parser.add_argument("--refs", nargs="*", default=None)
    parser.add_argument("--count", type=int, default=2)
    args = parser.parse_args()

    meta_file = OUTPUT_BASE / args.character / "character_meta.json"
    mannequin_file = OUTPUT_BASE / args.character / "mannequin_refs.json"
    project_id = args.project_id

    customizer = {
        "characterName": "Sở Tiêu Dao (Chu Xiaoyao)",
        "style": "2D Xianxia/Fantasy manhwa anime chibi sprite, bold clean linework, flat cel-shaded coloring, mature 4.8-5.0 heads ratio",
        "gender": "male",
        "age": "young adult (20-22)",
        "hairStyleColor": "Long silky natural black hair flowing loosely in soft rogue locks",
        "outfitDescription": "Two-layer rogue martial artist daoist robe",
        "primaryColor": "Muted Slate Cyan & Deep Indigo Linen",
        "accentColor": "Natural Flaxen Ivory & Charcoal Gray",
        "skinTone": "Fair warm ivory natural skin tone seamlessly matching neck and hands",
        "weaponType": "None (empty hands, pure martial arts)",
        "spellElement": "Tiêu dao thanh phong linh lực",
        "chromaBgHex": "#00FF00",
        "waistRearMotionLock": "strictly continuous flat belt band behind back, ZERO bow, ZERO ribbon knot",
    }

    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if not project_id:
            project_id = meta.get("project_id")
        profile = meta.get("profile", {})
        gender = meta.get("gender", "male")
        is_male = (gender.lower() == "male")
        rear_belt = (
            "strictly continuous flat belt band behind back, ZERO bow, ZERO ribbon knot"
            if is_male else
            "delicate silk ribbon sash draping calmly downward without flapping under natural gravity"
        )
        customizer = {
            "characterName": meta.get("name", "Character"),
            "style": profile.get("style", customizer["style"]),
            "gender": gender,
            "age": meta.get("age", profile.get("age", "young adult (20-22)")),
            "hairStyleColor": profile.get("hair", ""),
            "outfitDescription": profile.get("outfit", ""),
            "primaryColor": profile.get("primary_color", ""),
            "accentColor": profile.get("accent_color", ""),
            "skinTone": profile.get("skin", "Fair warm ivory natural healthy skin tone"),
            "weaponType": "None (empty hands, pure martial arts)",
            "spellElement": profile.get("combat_style", ""),
            "chromaBgHex": profile.get("chroma_bg", "#00FF00"),
            "waistRearMotionLock": rear_belt,
        }

    refs = args.refs
    if not refs:
        mannequin_refs = {}
        if mannequin_file.exists():
            with open(mannequin_file, "r", encoding="utf-8") as f:
                mannequin_refs = json.load(f)

        m_id = mannequin_refs.get(args.angle)
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        id_0 = meta.get("angle_0", {}).get("media_id")
        id_180 = meta.get("angle_180", {}).get("media_id")

        if args.angle == "135":
            # 135° rule: mannequin_135 FIRST, then angle_180
            refs = [m_id, id_180]
        else:
            refs = [id_0, m_id]

    if not project_id:
        raise ValueError("Project ID not found. Specify --project-id or set in character_meta.json")

    run_angle_batch(args.character, project_id, args.angle, refs, customizer, args.count)

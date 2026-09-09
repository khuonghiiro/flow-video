"""Stage 2A: Generate Dual-Ref Candidates for 45°, 90°, 180° simultaneously (Han Lang Phong)."""

import asyncio
import base64
import json
import logging
import os
import sys
import aiohttp

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stage2a_han_lang_phong")

PROJECT_ID = "09c32739-99ca-4d85-a250-558faf36d638"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\han-lang-phong"
MEDIA_ID_0 = "8bcd85e1-4c37-4f58-a92d-0546aabc19e4"

with open(os.path.join(OUTPUT_DIR, "mannequin_refs.json"), encoding="utf-8") as f:
    MANNEQUINS = json.load(f)

PROMPTS = {
    "45": (
        "2D Xianxia manhwa anime chibi character sprite — TRUE DEEP 45-DEGREE THREE-QUARTER ISOMETRIC VIEW.\n"
        "FIRST AND MOST IMPORTANT INSTRUCTION: ROTATE the character's ENTIRE BODY 45 degrees to face 10 o'clock (upper-left diagonal). STRICTLY FORBIDDEN to face camera directly. "
        "ASYMMETRICAL 3/4 DEPTH POSE: Left shoulder and left foot forward in foreground, right shoulder and right foot receding backward in depth. Chest plane visibly rotated 45 degrees diagonally away from camera. "
        "BLANK FACELESS HEAD: Completely blank smooth porcelain mannequin head turned 45 degrees left (NO eyes, NO nose, NO mouth). "
        "IDENTITY LOCK: Match 0° reference character: Hàn Lăng Phong, high heroic ponytail with silver metallic ring, layered fringe bangs, side locks, two-layered daoist martial robes with frost-white cross-collar inner robe and deep midnight indigo and slate teal outer robe with silver thunder embroidery, structured dark leather belt with rectangular silver plaque, flat black cloth martial boots with white soles, empty hands. "
        "STYLE: Pure flat 2D Xianxia manhwa anime chibi sprite illustration, clean linework, flat cel-shaded coloring, harmonious natural colors, zero neon glow. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "90": (
        "2D Xianxia manhwa anime chibi character sprite — TRUE 90-DEGREE PURE SIDE PROFILE VIEW.\n"
        "CAMERA & POSE: Character stands in strict 90-degree left side silhouette (facing exactly 9 o'clock direction). "
        "PURE LATERAL FLANK VIEW: Only left side of character is visible: left side of head, left shoulder, left sleeve, left side of indigo and slate teal robe, left hip, left leg, left flat cloth boot pointing directly to 9 o'clock. "
        "Right arm, right shoulder, and right leg are 100% occluded directly behind the body and invisible. STRICTLY ZERO FRONT VIEW, ZERO FRONT CHEST. Pure flank side silhouette. "
        "IDENTITY LOCK: Match 0° reference: Hàn Lăng Phong, high ponytail cascading backward, deep midnight indigo and slate teal robes, flat black boots. "
        "BLANK FACELESS HEAD: Pure smooth blank mannequin head in left side profile outline (NO eyes, NO nose, NO mouth). "
        "STYLE: Pure flat 2D Xianxia manhwa anime chibi illustration, bold clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "180": (
        "2D Xianxia manhwa anime chibi character sprite — TRUE 180-DEGREE FULL REAR VIEW.\n"
        "CAMERA & POSE: Character stands with spine vertical facing 100% DIRECTLY AWAY from camera (180° back view). "
        "CRITICAL: Symmetrical back view. Full back of silky black high ponytail cascading down along spine past waist, silver metallic hair ring viewed from behind, symmetrical back of deep midnight indigo and slate teal outer robe with silver thunder cloud embroidery. "
        "CRITICAL BELT BACK RULE: Plain flat continuous dark leather belt band behind back, STRICTLY CONTINUOUS FLAT BELT BAND BEHIND BACK, ZERO BOW, ZERO RIBBON KNOT. "
        "Both heels facing camera, feet pointing away symmetrically. Flat black cloth boots with white soles (STRICTLY FLAT, ZERO HEELS). "
        "IDENTITY LOCK: Match 0° reference character costume colors, deep midnight indigo, frost white inner hem, slate teal accents. Empty hands at sides. "
        "STYLE: Pure flat 2D Xianxia manhwa anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    )
}


async def generate_single(session: aiohttp.ClientSession, angle: str, cand_idx: int) -> dict:
    cand_name = f"angle_{angle}_c{cand_idx}"
    prompt = PROMPTS[angle]
    mannequin_id = MANNEQUINS.get(angle)
    # Dual-Ref: [Mannequin Pose Guide, 0° Master Identity]
    refs = [mannequin_id, MEDIA_ID_0] if mannequin_id else [MEDIA_ID_0]

    logger.info("Submitting %s (Dual-Ref: %s)...", cand_name, refs)
    url = "http://127.0.0.1:8100/api/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "character_media_ids": refs,
    }

    for attempt in range(4):
        try:
            async with session.post(url, json=body, timeout=120) as resp:
                data = await resp.json()
                media_list = data.get("media", [])
                if not media_list and isinstance(data.get("data"), dict):
                    media_list = data["data"].get("media", [])

                if not media_list:
                    logger.warning("%s attempt %d returned no media: %s", cand_name, attempt + 1, data)
                    await asyncio.sleep(4)
                    continue

                m = media_list[0]
                mid = m.get("name")
                gen_img = m.get("image", {}).get("generatedImage", {}) if isinstance(m.get("image"), dict) else {}
                img_url = (
                    m.get("fifeUrl")
                    or m.get("servingUri")
                    or gen_img.get("fifeUrl")
                    or gen_img.get("servingUri")
                )

                target_file = os.path.join(OUTPUT_DIR, f"{cand_name}.png")
                img_bytes = None
                if img_url:
                    async with session.get(img_url) as img_resp:
                        img_bytes = await img_resp.read()
                elif "image" in m and "encodedImage" in m["image"]:
                    img_bytes = base64.b64decode(m["image"]["encodedImage"])

                if img_bytes:
                    with open(target_file, "wb") as f:
                        f.write(img_bytes)
                    logger.info("Saved %s -> %s (media_id=%s, size=%d)", cand_name, target_file, mid, len(img_bytes))
                    return {"name": cand_name, "angle": angle, "candidate": cand_idx, "media_id": mid, "file": f"{cand_name}.png", "path": target_file, "size_bytes": len(img_bytes)}
        except Exception as e:
            logger.error("Exception in %s attempt %d: %s", cand_name, attempt + 1, e)
            await asyncio.sleep(4)

    return {"name": cand_name, "angle": angle, "candidate": cand_idx, "media_id": None, "file": None, "path": None, "size_bytes": 0}


async def main():
    logger.info("=== STARTING STAGE 2A: 45°, 90°, 180° PARALLEL GENERATION (6 REQUESTS) ===")
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Build 6 concurrent tasks (2 candidates for 45°, 2 for 90°, 2 for 180°)
        tasks = []
        for angle in ["45", "90", "180"]:
            for c in [1, 2]:
                tasks.append(generate_single(session, angle, c))

        results = await asyncio.gather(*tasks)

    valid_candidates = [r for r in results if r.get("media_id") and r.get("size_bytes", 0) > 0]
    out_meta = os.path.join(OUTPUT_DIR, "candidates_stage2a.json")
    with open(out_meta, "w", encoding="utf-8") as f:
        json.dump(valid_candidates, f, indent=2, ensure_ascii=False)

    print(f"\n[DONE] Stage 2A Complete: {len(valid_candidates)}/6 candidates generated!")
    for r in valid_candidates:
        print(f" -> {r['name']} ({r['angle']}° c{r['candidate']}): media_id={r['media_id']} | path={r['path']}")


if __name__ == "__main__":
    asyncio.run(main())

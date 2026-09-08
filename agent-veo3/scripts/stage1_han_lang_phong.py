"""Stage 1: Generate 3 Candidates for 0° Direct Front View (Han Lang Phong)."""

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
logger = logging.getLogger("stage1_han_lang_phong")

PROJECT_ID = "09c32739-99ca-4d85-a250-558faf36d638"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\han-lang-phong"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "dung-yen"), exist_ok=True)

MALE_MANNEQUINS_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\public\mannequins\male"

PROMPT_0 = (
    "MASTER CHARACTER DESIGN — 2D XIANXIA/MANHWA CHIBI MALE SPRITE — 0° DIRECT FRONTAL VIEW\n"
    "CRITICAL ANATOMICAL PROPORTION & SCALE LOCK: Mature stylized semi-chibi manhwa anime sprite proportion (~4.8 to 5.0 heads tall, full-body vertical height occupies 85-88% canvas height). "
    "Head size is proportionate and balanced with broad masculine shoulders; strictly ZERO oversized giant chibi head, ZERO shrunken tiny torso, ZERO bobblehead deformity. "
    "Clean masculine waist, long straight legs grounded firmly on floor plane.\n"
    "CAMERA & POSE: Character MUST face 100% DIRECTLY forward at camera (strict 0.0° front view). "
    "Head facing 100% straight forward towards viewer. NO head turn, NO head tilt, NO 3/4 angle. "
    "Symmetrical standing pose, torso upright, shoulders level, both arms relaxed straight down along sides, empty bare hands. "
    "Both feet planted parallel and pointing directly forward towards viewer (12 o'clock). "
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and coat hems hang straight down naturally under calm gravity. Strictly NO wind blowing, NO billowing fabric, NO flapping hems. "
    "CRITICAL — BLANK FACELESS HEAD & UNIFORM SKIN: Completely BLANK, SMOOTH, FEATURELESS face surface. "
    "NO eyes, NO eyebrows, NO nose, NO mouth. Facial skin color MUST seamlessly and uniformly match the neck and hands (fair warm ivory healthy skin tone) with 100% consistency. "
    "CRITICAL — ZERO WEAPONS OR PROPS: Strictly NO weapons, NO swords, NO props. Hands are empty and resting naturally. "
    "HAIR: Silky jet-black hair tied in a high heroic ponytail with a sleek silver metallic ring, layered fringe bangs naturally framing forehead, two soft face-framing sidelocks hugging cheeks, back ponytail cascading smoothly down along back. "
    "OUTFIT: Two-layered flowing Xianxia daoist martial robes: crisp frost-white silk inner robe with diagonal cross-collar wrap, deep midnight indigo and slate teal silk outer robe with delicate celestial silver lightning cloud embroidery along lapels and sleeve cuffs, structured dark leather waist belt with silver thunder pattern rectangular plaque, wide flowing sleeves hanging straight down naturally, straight double-slit robe hem draping naturally to ankles. "
    "SHOES: Flat black cloth martial boots with white soles (strictly flat soles, zero heels). "
    "COLORS: Deep Midnight Indigo & Frost White, Slate Teal & Celestial Silver accents. "
    "STYLE: Pure flat 2D Xianxia manhwa anime chibi illustration, bold clean linework, flat cel-shaded coloring, harmonious natural colors, zero neon glow. "
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible from head crown to feet."
)


async def upload_mannequins(session: aiohttp.ClientSession) -> dict:
    url = "http://127.0.0.1:8100/api/flow/upload-image"
    angles = ["0", "45", "90", "135", "180"]
    uploaded = {}
    for a in angles:
        fpath = os.path.join(MALE_MANNEQUINS_DIR, f"angle_{a}.png")
        fname = f"mannequin_male_{a}.png"
        payload = {
            "file_path": fpath,
            "project_id": PROJECT_ID,
            "file_name": fname,
        }
        logger.info("Uploading male mannequin %s°...", a)
        async with session.post(url, json=payload, timeout=30) as resp:
            data = await resp.json()
            mid = data.get("media_id")
            uploaded[a] = mid
            logger.info("Uploaded mannequin %s° -> media_id: %s", a, mid)
    return uploaded


async def generate_single_candidate(session: aiohttp.ClientSession, idx: int, refs: list) -> dict:
    gen_url = "http://127.0.0.1:8100/api/flow/generate-image"
    payload = {
        "prompt": PROMPT_0,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
    }
    if refs:
        payload["character_media_ids"] = refs

    logger.info("Submitting Candidate #%d...", idx)
    try:
        async with session.post(gen_url, json=payload, timeout=120) as resp:
            data = await resp.json()
            media_list = data.get("media", [])
            if not media_list and isinstance(data.get("data"), dict):
                media_list = data["data"].get("media", [])

            if not media_list:
                logger.warning("Candidate #%d returned no media: %s", idx, data)
                return {"candidate": idx, "error": data}

            m = media_list[0]
            mid = m.get("name")
            gen_img = m.get("image", {}).get("generatedImage", {}) if isinstance(m.get("image"), dict) else {}
            img_url = (
                m.get("fifeUrl")
                or m.get("servingUri")
                or gen_img.get("fifeUrl")
                or gen_img.get("servingUri")
            )
            encoded = gen_img.get("encodedImage")

            img_bytes = None
            if img_url:
                async with session.get(img_url) as img_resp:
                    img_bytes = await img_resp.read()
            elif encoded:
                img_bytes = base64.b64decode(encoded)

            if not img_bytes:
                logger.warning("No image bytes for candidate #%d", idx)
                return {"candidate": idx, "error": "no_bytes"}

            out_path = os.path.join(OUTPUT_DIR, f"candidate_0_{idx}.png")
            with open(out_path, "wb") as f:
                f.write(img_bytes)

            logger.info("Candidate #%d saved: %s (media_id=%s, size=%d)", idx, out_path, mid, len(img_bytes))
            return {
                "candidate": idx,
                "media_id": mid,
                "file": f"candidate_0_{idx}.png",
                "path": out_path,
                "size_bytes": len(img_bytes),
            }
    except Exception as e:
        logger.error("Exception generating candidate #%d: %s", idx, e)
        return {"candidate": idx, "error": str(e)}


async def main():
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Step 1: Upload male mannequins if not done
        mannequin_map_file = os.path.join(OUTPUT_DIR, "mannequin_refs.json")
        if not os.path.exists(mannequin_map_file):
            mannequin_map = await upload_mannequins(session)
            with open(mannequin_map_file, "w") as f:
                json.dump(mannequin_map, f, indent=2)
            logger.info("Saved mannequin map: %s", mannequin_map)
        else:
            with open(mannequin_map_file) as f:
                mannequin_map = json.load(f)
            logger.info("Loaded existing mannequin map: %s", mannequin_map)

        mannequin_0 = mannequin_map.get("0")
        refs = [mannequin_0] if mannequin_0 else []

        # Step 2: Generate 3 candidates in parallel
        logger.info("=== GENERATING BATCH OF 3 CANDIDATES FOR 0° IN PARALLEL ===")
        tasks = [generate_single_candidate(session, i, refs) for i in range(1, 4)]
        candidates = await asyncio.gather(*tasks)

        valid_candidates = [c for c in candidates if "media_id" in c and c.get("size_bytes", 0) > 0]
        meta_file = os.path.join(OUTPUT_DIR, "candidates_0.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(valid_candidates, f, indent=2, ensure_ascii=False)

        print(f"\n[DONE] Generated {len(valid_candidates)}/3 candidates for 0°! See {meta_file}")
        for c in valid_candidates:
            print(f" -> Candidate #{c['candidate']}: media_id={c['media_id']} | path={c['path']}")


if __name__ == "__main__":
    asyncio.run(main())

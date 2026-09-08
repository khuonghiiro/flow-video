import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "7de76f25-e719-452f-8a03-fb6eece897e4"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\da-vo-nhai"

mid_0 = "62a88991-c3d8-4fb5-8cf0-23da064aba43"

PROMPT_45 = (
    "2D Xianxia anime chibi character sprite — TRUE THREE-QUARTER VIEW 45 DEGREES.\n"
    "POSE & CAMERA: Character body and head are turned 45 degrees towards the left (facing diagonal 10 o'clock direction). "
    "CRITICAL: The chest and torso plane are visibly angled diagonally at 45 degrees toward the left, NOT facing front. "
    "Left shoulder is clearly positioned forward in the foreground; right shoulder is pulled back in depth and recessed behind the neck. "
    "Both feet are planted and point diagonally toward the left (10 o'clock direction).\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and outer coat hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO COAT TAILS FLYING BACKWARD. Calm static fabric drape.\n"
    "HAIRSTYLE & IDENTITY: Keep 100% identical high topknot with sleek golden coronet and hairpin, "
    "slender side strands, and long straight silky black hair flowing down the back.\n"
    "SKIN TONE: Smooth pale fair ivory-white skin tone matching references 100% seamlessly on face, neck, and hands.\n"
    "COSTUME (IDENTICAL RICH DETAILS): Exact same midnight ink-navy martial coat over crisp white inner robe with diagonal collar, "
    "intricate golden cloud patterns and dragon filigree embroidery along lapels, cuffs, and hem. "
    "Broad black waist belt with dual gold border bands and circular gold-framed white jade medallion. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS. "
    "Loose white trousers, flat black cloth boots with gold stitching and flat white soles.\n"
    "ARMS: Left arm in foreground, right arm recessed, empty bare hands, strictly zero weapons, zero props.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
)

PROMPT_180 = (
    "2D Xianxia anime chibi character sprite — FULL BACK VIEW (STRICT 180.0 DEGREES REAR).\n"
    "PERFECT SYMMETRICAL DIRECT REAR POSE: Character turned 100% away from camera, facing 12 o'clock away from viewer. "
    "Back of head visible with neat high topknot and sleek golden hairpin/coronet. "
    "Long silky black hair falls straight down the exact center of the spine. "
    "Both shoulders are level, horizontal, and symmetrical from behind. "
    "Both feet are planted parallel, heels facing camera.\n"
    "COSTUME & FABRIC (STRICTLY FLAT MATTE, ZERO SHINE): Midnight ink-navy outer daoist martial robe seen from behind. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS. "
    "Natural flat cel-shaded cloth, intricate golden cloud embroidery along outer sleeve cuffs and lower coat hem.\n"
    "CRITICAL WAIST BELT REAR: Broad black belt with dual gold border bands wraps smoothly and flatly around the lower back. "
    "STRICTLY CONTINUOUS FLAT BELT BAND AROUND REAR WITH ZERO BOW, ZERO RIBBON KNOT, ZERO DECORATIVE TIES. Completely smooth flat belt at rear.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robe, coat tails, and sleeves hang straight down naturally under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING COAT TAILS, NO HEMS FLYING. Calm static fabric drape.\n"
    "Loose white trousers, and flat black cloth boots seen from behind.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible."
)

async def generate_cand(session, name, prompt, ref_ids):
    url = "http://127.0.0.1:8100/api/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "character_media_ids": ref_ids
    }
    for attempt in range(3):
        print(f"Generating {name} (attempt {attempt+1})...", flush=True)
        try:
            async with session.post(url, json=body, timeout=120) as resp:
                data = await resp.json()
                media_list = data.get("media", [])
                if not media_list:
                    print(f"Fail {name}: {data}", flush=True)
                    await asyncio.sleep(4)
                    continue
                m = media_list[0]
                mid = m.get("name")
                gen_img = m.get("image", {}).get("generatedImage", {})
                img_url = (
                    m.get("fifeUrl")
                    or m.get("servingUri")
                    or gen_img.get("fifeUrl")
                    or gen_img.get("servingUri")
                    or m.get("image", {}).get("fifeUrl")
                    or m.get("image", {}).get("servingUri")
                )
                
                target_file = os.path.join(OUTPUT_DIR, f"{name}.png")
                if img_url:
                    async with session.get(img_url) as img_resp:
                        content = await img_resp.read()
                        with open(target_file, "wb") as f:
                            f.write(content)
                    print(f"Done {name}! Media ID: {mid}, Size: {os.path.getsize(target_file)}", flush=True)
                    return name, mid, target_file
                elif "image" in m and "encodedImage" in m["image"]:
                    import base64
                    with open(target_file, "wb") as f:
                        f.write(base64.b64decode(m["image"]["encodedImage"]))
                    print(f"Done {name} (b64)! Media ID: {mid}, Size: {os.path.getsize(target_file)}", flush=True)
                    return name, mid, target_file
        except Exception as e:
            print(f"Error {name}: {e}", flush=True)
            await asyncio.sleep(4)
    return name, None, None

async def main():
    print("Generating Stage 2A (45° and 180°) for Da Vo Nhai...", flush=True)
    results = []
    async with aiohttp.ClientSession() as session:
        c_45_1 = await generate_cand(session, "angle_45_c1", PROMPT_45, [mid_0])
        await asyncio.sleep(3)
        c_45_2 = await generate_cand(session, "angle_45_c2", PROMPT_45, [mid_0])
        await asyncio.sleep(3)
        c_180_1 = await generate_cand(session, "angle_180_c1", PROMPT_180, [mid_0])
        await asyncio.sleep(3)
        c_180_2 = await generate_cand(session, "angle_180_c2", PROMPT_180, [mid_0])
        results = [c_45_1, c_45_2, c_180_1, c_180_2]
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "stage2a_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed Stage 2A:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

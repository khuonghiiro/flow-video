import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "1bbd5b67-bb64-4726-a6f7-6a0060a06718"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\lang-van-chu"

mid_0 = "ffe04bbd-4dbb-4026-be49-7f7a84be9953"
mid_45 = "1db3c44d-038e-41b5-a2c8-9fab1a170740"

PROMPT_90 = (
    "2D Xianxia anime chibi character sprite — FULL LATERAL LEFT SIDE VIEW (STRICT 90.0 DEGREES PROFILE).\n"
    "PERFECT 90-DEGREE LATERAL PROFILE: Character turned 90 degrees to the left, facing 9 o'clock direction. "
    "Only the character's left side of body is visible; the right side is completely occluded behind. "
    "Lateral side profile of blank faceless head (smooth featureless blank face, no nose, no eyes, no mouth). "
    "Left ear visible, neat high topknot with silver hairpin seen in pure profile, long black hair falls straight down the back.\n"
    "SKIN TONE: Smooth pale fair ivory-white skin tone matching references 100% seamlessly across neck and left hand.\n"
    "COSTUME & FABRIC (STRICTLY FLAT MATTE, ZERO SHINE): Exact same light dove-grey daoist martial robe from references. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS, ZERO SATIN SHEEN. "
    "Left sleeve with ink-black cloud embroidery at cuff. "
    "Broad black structured waist belt with silver borders seen from the side, wrapping flat against waist. "
    "Loose white trousers, flat black cloth boots pointing 9 o'clock.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and coat hem hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO COAT TAILS FLYING BACKWARD. Calm static fabric drape.\n"
    "Left arm rests relaxed at side, empty bare hand, strictly zero weapons, zero props, zero swords.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible."
)

PROMPT_180 = (
    "2D Xianxia anime chibi character sprite — FULL BACK VIEW (STRICT 180.0 DEGREES REAR).\n"
    "PERFECT SYMMETRICAL DIRECT REAR POSE: Character turned 100% away from camera, facing 12 o'clock away from viewer. "
    "Back of head visible with neat high topknot and sleek silver hairpin piercing horizontally. "
    "Long silky black hair falls straight down the exact center of the spine. "
    "Both shoulders are level, horizontal, and symmetrical from behind. "
    "Both feet are planted parallel, heels facing camera.\n"
    "COSTUME & FABRIC (STRICTLY FLAT MATTE, ZERO SHINE): Light dove-grey daoist robe seen from behind. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS, ZERO SATIN SHEEN. "
    "Natural flat cel-shaded cloth texture, subtle cloud embroidery on outer sleeve cuffs.\n"
    "CRITICAL WAIST BELT REAR: Broad black structured belt with silver borders wraps smoothly around the lower back. "
    "STRICTLY FLAT CONTINUOUS BELT BAND AROUND REAR WITH ZERO BOW, ZERO RIBBON KNOT, ZERO DECORATIVE TIES. Completely smooth flat belt at rear.\n"
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
    print("Generating fixed 90° and 180° candidates matching pale skin & matte cloth...", flush=True)
    results = []
    async with aiohttp.ClientSession() as session:
        # 90° candidates (ref: 0° + 45°)
        c_90_1 = await generate_cand(session, "angle_90_fixed_c1", PROMPT_90, [mid_0, mid_45])
        await asyncio.sleep(3)
        c_90_2 = await generate_cand(session, "angle_90_fixed_c2", PROMPT_90, [mid_0, mid_45])
        await asyncio.sleep(3)
        
        # 180° candidates (ref: 0°)
        c_180_1 = await generate_cand(session, "angle_180_fixed_c1", PROMPT_180, [mid_0])
        await asyncio.sleep(3)
        c_180_2 = await generate_cand(session, "angle_180_fixed_c2", PROMPT_180, [mid_0])
        
        results = [c_90_1, c_90_2, c_180_1, c_180_2]
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "fixed_90_180_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed generation of 90° and 180° candidates:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

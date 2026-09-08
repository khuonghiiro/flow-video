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
    "2D Xianxia anime chibi character sprite — TRUE THREE-QUARTER VIEW (45 DEGREES).\n"
    "CRITICAL SCALE & STATURE LOCK: Maintain the EXACT SAME TALL, SLENDER, ATHLETIC HEIGHT AND FULL-BODY PROPORTIONS as Reference 0°. "
    "The character MUST occupy the exact same vertical percentage of the canvas (~88% vertical height from top of golden coronet to bottom of boots). "
    "STRICTLY ZERO SHRINKING, ZERO ZOOM-OUT, ZERO COMPRESSION OF STATURE, ZERO MINIATURIZATION. Identical camera distance and framing.\n"
    "PRESERVE 100% INTRICATE DETAILS: Faithfully preserve EVERY detail from Reference 0°: "
    "the intricate flowing golden cloud patterns and dragon-rune embroidery along the lapels, wide sleeve cuffs, and lower coat hem borders. "
    "Exact crisp white inner robe with diagonal collar trimmed in gold, broad black silk waist belt with dual gold borders and central circular gold-framed white jade medallion.\n"
    "ROTATED 45-DEGREE POSE: The entire body, chest, and hips are ROTATED 45 DEGREES to the left (facing diagonal 10 o'clock direction). "
    "Left shoulder is clearly forward in foreground; right shoulder is recessed behind the neck. "
    "Left foot steps forward pointing 10 o'clock; right foot placed slightly behind pointing 10 o'clock. "
    "Diagonal V-neck crossover lapel clearly angles across the 3/4 chest plane. "
    "Head is turned 45 degrees to the left showing left ear and 3/4 jawline.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and outer coat hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO COAT TAILS FLYING BACKWARD. Calm static fabric drape.\n"
    "SKIN TONE: Smooth pale fair ivory-white skin tone matching reference 100% seamlessly on face, neck, and hands.\n"
    "HAIRSTYLE: High topknot with sleek golden coronet and hairpin, slender side strands, silky black hair flowing down the back.\n"
    "Empty bare hands, strictly zero weapons, zero props. Flat black cloth boots with gold stitching and flat white soles.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, harmonious rich palette, strictly zero neon glow.\n"
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
    print("Re-generating 45° referencing ONLY 0° with Scale Lock...", flush=True)
    async with aiohttp.ClientSession() as session:
        c1 = await generate_cand(session, "angle_45_ref0_c1", PROMPT_45, [mid_0])
        await asyncio.sleep(3)
        c2 = await generate_cand(session, "angle_45_ref0_c2", PROMPT_45, [mid_0])
    print("Done 45° ref 0:", [c1, c2], flush=True)

if __name__ == "__main__":
    asyncio.run(main())

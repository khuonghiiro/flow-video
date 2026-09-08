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
mid_45 = "f0d8d691-9896-491b-909d-521ff856191e"

PROMPT_90 = (
    "2D Xianxia anime chibi character sprite — FULL LATERAL LEFT SIDE VIEW (STRICT 90.0 DEGREES PROFILE).\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate between Reference 0° (front view) and Reference 45° (three-quarter view).\n"
    "CRITICAL SCALE & STATURE LOCK: Maintain the EXACT SAME TALL, SLENDER, ATHLETIC HEIGHT AND FULL-BODY PROPORTIONS as References [0°, 45°]. "
    "The character MUST occupy the exact same vertical percentage of the canvas (~88% vertical height from top of golden coronet to bottom of boots). "
    "STRICTLY ZERO SHRINKING, ZERO ZOOM-OUT, ZERO COMPRESSION OF STATURE. Identical camera framing and tall stature.\n"
    "PRESERVE 100% INTRICATE DETAILS: Preserve EVERY rich detail from references: "
    "the intricate flowing golden cloud patterns and dragon-rune embroidery along the wide left sleeve cuff and lower coat hem borders. "
    "Broad black-and-gold waist belt wrapping flat against waist. "
    "Loose white trousers, flat black cloth boots with gold cloud stitching pointing strictly 9 o'clock.\n"
    "PERFECT 90-DEGREE LATERAL PROFILE: Character turned 90 degrees to the left, facing 9 o'clock direction. "
    "Only the character's left side of body is visible; the right side is completely occluded behind. "
    "Lateral side profile of blank faceless head, left ear visible, neat high topknot with sleek golden coronet and hairpin seen in pure profile, silky black hair falls straight down the back.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and coat hem hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO COAT TAILS FLYING BACKWARD. Calm static fabric drape.\n"
    "Left arm rests relaxed at side, empty bare hand, strictly zero weapons, zero props, zero swords.\n"
    "SKIN TONE: Smooth pale fair ivory-white skin tone matching references 100% seamlessly on neck and left hand.\n"
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
    print("Re-generating 90° referencing [0°, 45°] with Scale Lock and Full Details...", flush=True)
    async with aiohttp.ClientSession() as session:
        c1 = await generate_cand(session, "angle_90_ref0_45_c1", PROMPT_90, [mid_0, mid_45])
        await asyncio.sleep(3)
        c2 = await generate_cand(session, "angle_90_ref0_45_c2", PROMPT_90, [mid_0, mid_45])
    print("Done 90° ref [0, 45]:", [c1, c2], flush=True)

if __name__ == "__main__":
    asyncio.run(main())

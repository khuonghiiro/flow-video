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
mid_90 = "0bdb8722-0411-4fde-baa9-a9dc112f9406"

PROMPT_45_FINE = (
    "2D Xianxia anime chibi character sprite — DYNAMIC ASYMMETRICAL 45-DEGREE THREE-QUARTER VIEW.\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate exactly halfway between Reference 0° (front view) and Reference 90° (lateral side profile).\n"
    "CRITICAL ROTATED 3/4 POSE: Entire body, chest, torso, and hips are visibly angled 45 degrees to the left (facing diagonal 10 o'clock direction). "
    "STRICTLY ASYMMETRICAL 3/4 STEPPING STANCE: Left shoulder is prominently in the foreground; right shoulder is deeply recessed in depth behind the neck. "
    "Left foot steps forward pointing 10 o'clock; right foot is placed slightly behind pointing 10 o'clock. "
    "The diagonal V-neck collar lapel clearly crosses diagonally from right to left across the angled chest. "
    "Head is turned 45 degrees to the left showing left ear and 3/4 jawline.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and outer coat hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO COAT TAILS FLYING BACKWARD. Calm static fabric drape.\n"
    "HAIRSTYLE & IDENTITY: Keep 100% identical high topknot with sleek golden coronet and hairpin, "
    "two slender side hair strands, and long straight silky black hair flowing down the back.\n"
    "SKIN TONE: Smooth pale fair ivory-white skin tone matching references 100% seamlessly on face, neck, and hands.\n"
    "COSTUME: Exact same midnight ink-navy martial coat over crisp white inner robe with diagonal collar, "
    "intricate golden cloud patterns and dragon filigree embroidery along lapels, cuffs, and hem. "
    "Broad black waist belt with dual gold border bands and circular gold-framed white jade medallion. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS. "
    "Loose white trousers, flat black cloth boots with gold stitching and flat white soles.\n"
    "Empty bare hands, strictly zero weapons, zero props.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
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
    print("Fine-tuning 45° for Da Vo Nhai...", flush=True)
    async with aiohttp.ClientSession() as session:
        c1 = await generate_cand(session, "angle_45_step_1", PROMPT_45_FINE, [mid_0, mid_90])
        await asyncio.sleep(3)
        c2 = await generate_cand(session, "angle_45_step_2", PROMPT_45_FINE, [mid_0, mid_90])
    print("Completed fine 45°:", [c1, c2], flush=True)

if __name__ == "__main__":
    asyncio.run(main())

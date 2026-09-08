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
mid_180 = "9373315a-d67e-45a3-a38d-d9aba582c46b"

PROMPT_135 = (
    "2D Xianxia anime chibi character sprite — THREE-QUARTER REAR VIEW (135 DEGREES).\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate between Reference 0° (front) and Reference 180° (rear). "
    "Character turned away from camera, viewing the back-left side of character (facing 1:30 o'clock direction / body rotated 135 degrees). "
    "The character's back is angled in distinct 3/4 perspective: the left shoulder and left sleeve are in the foreground, "
    "while the right shoulder is recessed into the background. "
    "The spine and back-seam are viewed at a diagonal 135-degree angle.\n"
    "HAIRSTYLE & IDENTITY: High topknot with silver hairpin seen in 3/4 rear angle, "
    "long black hair flowing straight down the diagonal back.\n"
    "SKIN TONE: Smooth pale fair ivory-white anime skin tone matching references 100% seamlessly on neck and hands.\n"
    "COSTUME & FABRIC (STRICTLY FLAT MATTE, ZERO SHINE): Exact same light dove-grey daoist martial robe. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS, ZERO SATIN SHEEN. "
    "Natural flat cel-shaded cloth, ink-black cloud embroidery on outer sleeve cuffs.\n"
    "CRITICAL WAIST BELT REAR: Broad black structured belt with silver borders wraps smoothly around the lower back. "
    "STRICTLY FLAT CONTINUOUS BELT BAND AROUND REAR WITH ZERO BOW, ZERO RIBBON KNOT, ZERO DECORATIVE TIES. Completely smooth flat belt at rear.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robe, coat tails, and sleeves hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING COAT TAILS, NO HEMS FLYING. Calm static fabric drape.\n"
    "Loose white trousers, and flat black cloth boots pointing away at 135 degrees.\n"
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
    print("Generating fixed 135° candidates matching matte cloth and flat belt...", flush=True)
    results = []
    async with aiohttp.ClientSession() as session:
        c1 = await generate_cand(session, "angle_135_fixed_c1", PROMPT_135, [mid_0, mid_180])
        await asyncio.sleep(3)
        c2 = await generate_cand(session, "angle_135_fixed_c2", PROMPT_135, [mid_0, mid_180])
        results = [c1, c2]
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "fixed_135_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed generation of 135° candidates:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

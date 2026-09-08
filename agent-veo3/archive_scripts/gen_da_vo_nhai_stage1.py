import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "7de76f25-e719-452f-8a03-fb6eece897e4"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\da-vo-nhai"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PROMPT_0 = (
    "2D Xianxia anime chibi character sprite — MASTER CHARACTER DESIGN, FULL DIRECT FRONTAL VIEW (STRICT 0.0 DEGREES).\n"
    "PERFECT SYMMETRICAL DIRECT FRONTAL POSE: Character stands facing 100% DIRECTLY forward towards camera. "
    "Both shoulders are perfectly horizontal, level, and balanced. "
    "The chest and torso face 100% straight forward towards the viewer with absolute bilateral symmetry. "
    "Both legs are straight and parallel; both feet are planted parallel and point directly forward towards the viewer (12 o'clock). "
    "Head is perfectly upright, centered, zero head tilt, zero head turn.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and outer coat hang straight down naturally under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO FLYING COAT TAILS. Calm static fabric drape.\n"
    "BLANK FACELESS HEAD & PALE FAIR SKIN: Smooth featureless blank head with NO eyes, NO nose, NO mouth. "
    "The facial skin is a completely uniform, smooth pale fair ivory-white skin tone that matches the neck and hands 100% seamlessly. "
    "Clean flat cel-shaded anime skin, strictly zero facial features.\n"
    "HAIRSTYLE: Jet-black silky hair styled into a high neat topknot secured with an elegant golden coronet and hairpin, "
    "two delicate slender hair strands framing the sides of the face, and long straight black hair falling down the center of the back.\n"
    "COSTUME (EXTREMELY DETAILED & LUXURIOUS): Layered Xianxia daoist martial robe. "
    "Crisp snow-white silk inner robe with diagonal crossover collar trimmed in gold embroidery. "
    "Outer midnight ink-navy martial coat richly adorned with intricate flowing golden cloud patterns and dragon-rune filigree along the lapels, wide sleeve cuffs, and lower hem. "
    "Broad black silk waist sash with dual gold border bands and a structured circular white jade medallion framed in polished gold at the center navel. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS, ZERO SATIN SHEEN. "
    "Loose snow-white martial trousers, flat black cloth boots with subtle gold cloud stitching and flat white soles (CRITICAL: flat soles, strictly zero heels).\n"
    "ARMS & HANDS: Both arms rest relaxed and symmetrically at sides with open empty hands, bare hands, strictly zero weapons, zero swords, zero props.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, harmonious rich palette, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible from head to toe."
)

async def generate_cand(session, name, prompt, ref_ids=None):
    url = "http://127.0.0.1:8100/api/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
    }
    if ref_ids:
        body["character_media_ids"] = ref_ids

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
    print(f"Starting Stage 1 for Da Vo Nhai (Project: {PROJECT_ID})...", flush=True)
    async with aiohttp.ClientSession() as session:
        c1 = await generate_cand(session, "angle_0_c1", PROMPT_0)
        await asyncio.sleep(3)
        c2 = await generate_cand(session, "angle_0_c2", PROMPT_0)
        results = [c1, c2]
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "stage1_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed Stage 1:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "1bbd5b67-bb64-4726-a6f7-6a0060a06718"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\lang-van-chu"
REF_45_ID = "1db3c44d-038e-41b5-a2c8-9fab1a170740"  # Winning 45° with pale white skin & matte fabric

PROMPT_0_REF = (
    "2D Xianxia anime chibi character sprite — MASTER CHARACTER DESIGN, FULL DIRECT FRONTAL VIEW (STRICT 0.0 DEGREES).\n"
    "REFERENCE SYNCHRONIZATION: 100% faithful replication of character reference image. "
    "Exact pale fair ivory-white skin tone, exact matte dove-grey robe fabric, exact hairstyle with high topknot, exact black-and-silver belt structure.\n"
    "PERFECT SYMMETRICAL DIRECT FRONTAL POSE: Character stands facing 100% DIRECTLY forward towards camera. "
    "Both shoulders are perfectly horizontal, level, and balanced. "
    "The chest and torso face 100% straight forward towards the viewer with absolute bilateral symmetry. "
    "Both legs are straight and parallel; both feet are planted parallel and point directly forward towards the viewer (12 o'clock). "
    "Head is perfectly upright, centered, zero head tilt, zero head turn.\n"
    "BLANK FACELESS HEAD & PALE FAIR SKIN: Smooth featureless blank head with NO eyes, NO nose, NO mouth. "
    "The facial skin is a completely uniform, smooth pale fair ivory-white anime skin tone that matches the neck and hands 100% seamlessly, exactly like in the reference image. "
    "Clean flat cel-shaded skin, strictly zero facial features.\n"
    "COSTUME & FABRIC (STRICTLY FLAT MATTE, ZERO SHINE): Light dove-grey daoist robe over crisp white inner robe with diagonal collar wrap, "
    "delicate ink-black cloud embroidery along lapels and sleeve cuffs. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS, ZERO SATIN SHEEN. Completely natural flat cel-shaded cloth.\n"
    "WAIST BELT: Broad black structured waist belt with upper and lower silver/white trim borders and a silver-framed white jade buckle in center, identical to reference image.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and outer coat hang straight down naturally under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO FLYING COAT TAILS. Calm static fabric drape.\n"
    "Loose white trousers, and flat black cloth boots with white soles (flat soles, strictly zero heels).\n"
    "ARMS & HANDS: Both arms rest relaxed and symmetrically at sides with open empty hands, bare hands, strictly zero weapons, zero swords, zero props.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, harmonious natural colors, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible from head to toe."
)

PROMPT_0_TEXT = (
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
    "HAIRSTYLE: Jet-black hair styled into a neat high topknot with a delicate sleek silver hairpin, "
    "with silky long black hair falling straight down the center of the back.\n"
    "COSTUME: Soft pale dove-grey matte cotton-linen daoist martial robe over a crisp white inner robe with diagonal collar wrap, "
    "delicate ink-black cloud embroidery along lapels and sleeve cuffs. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS. "
    "Broad structured black waist belt with upper and lower silver borders and a silver-framed white jade center buckle, wrapping tightly and flatly around the waist. "
    "Loose white martial trousers, and flat black cloth boots with white soles (flat soles, strictly zero heels).\n"
    "ARMS & HANDS: Both arms rest relaxed and symmetrically at sides with open empty hands, bare hands, strictly zero weapons, zero swords, zero props.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, harmonious natural colors, strictly zero neon glow.\n"
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
    print("Generating fixed 0° candidates matching Image 1 pale skin & matte fabric...", flush=True)
    results = []
    async with aiohttp.ClientSession() as session:
        # Candidate 1: with reference to winning 45°
        c1 = await generate_cand(session, "angle_0_fixed_ref1", PROMPT_0_REF, [REF_45_ID])
        await asyncio.sleep(3)
        # Candidate 2: with reference to winning 45°
        c2 = await generate_cand(session, "angle_0_fixed_ref2", PROMPT_0_REF, [REF_45_ID])
        await asyncio.sleep(3)
        # Candidate 3: text only without reference
        c3 = await generate_cand(session, "angle_0_fixed_text", PROMPT_0_TEXT)
        results = [c1, c2, c3]
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "fixed_0_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed generation of fixed 0° candidates:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "1bbd5b67-bb64-4726-a6f7-6a0060a06718"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\lang-van-chu"

mid_0 = "e35e92f2-82f5-4e23-8842-ddc477e0b5eb"
mid_90 = "d47853b0-bfa0-4d7f-b3a0-fc31ce406973"
mid_180 = "bd6de5f0-3144-4116-9ecd-cbcf74dbd878"

PROMPT_45 = (
    "2D Xianxia anime chibi character sprite — TRUE 45-DEGREE THREE-QUARTER VIEW.\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate exactly halfway between Reference 0° (front view) and Reference 90° (lateral side profile).\n"
    "CRITICAL ROTATED TORSO & SHOULDERS: The character's entire upper body, torso, chest, and hips are ROTATED EXACTLY 45 DEGREES to the left (facing 10:30 o'clock direction). "
    "The chest plane is visibly angled diagonally at 45 degrees toward the left, NOT facing camera. "
    "The character's left shoulder is clearly positioned forward in the foreground; "
    "the right shoulder is positioned further back in depth and recessed behind the neck. "
    "The diagonal V-neck collar lapel crosses cleanly from right to left across the angled chest in 3/4 perspective. "
    "Both feet are planted and point diagonally toward the left (10 o'clock direction).\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: The silvery moon-grey silk daoist robe, sleeves, and hem hang straight down naturally under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO COAT TAILS FLYING BACKWARD. Calm static fabric drape.\n"
    "HAIRSTYLE & IDENTITY: Keep 100% identical hairstyle from references: black hair styled into high topknot with delicate silver hairpin, "
    "with long straight black hair flowing down the back.\n"
    "COSTUME: Exact same silvery moon-grey silk martial robe over crisp white inner robe with subtle ink-black cloud embroidery along lapels and sleeve cuffs, "
    "broad black-and-silver structured waist belt with centered white jade plaque, loose white martial trousers, and flat black cloth boots with white soles.\n"
    "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Completely featureless smooth blank face in 3/4 perspective, perfectly uniform natural fair warm healthy skin tone matching the neck and hands. "
    "STRICTLY ZERO WEAPONS, zero swords, zero instruments, zero props, zero neon glow. "
    "STYLE: Pure flat 2D anime chibi sprite illustration, crisp clean line art, flat cel-shading. "
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
)

PROMPT_135 = (
    "2D Xianxia anime chibi character sprite — THREE-QUARTER REAR VIEW (135 DEGREES).\n"
    "Character turned away from camera, viewing the back-left side of character (facing 1:30 o'clock direction / body rotated 135 degrees). "
    "The character's back is angled in distinct 3/4 perspective: the left shoulder and left sleeve are in the foreground, "
    "while the right shoulder is recessed deep into the background. "
    "The spine and back-seam are viewed at a diagonal 135-degree angle.\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate between Reference 0° (front) and Reference 180° (rear). "
    "Keep 100% identical costume and hair: high topknot with silver hairpin seen in 3/4 rear angle, "
    "long black hair flowing down the diagonal back, exact same silvery moon-grey robe with silver cloud embroidery.\n"
    "CRITICAL WAIST BELT REAR: Broad black-and-silver belt wraps smoothly and flatly around the lower back. "
    "STRICTLY CONTINUOUS FLAT BELT BAND AROUND BACK WITH ZERO BOW, ZERO RIBBON KNOT, ZERO DECORATIVE TIES. Completely smooth flat belt at rear.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robe and sleeves hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING COAT TAILS, NO HEMS FLYING. "
    "Loose white trousers, and flat black cloth boots pointing away at 135 degrees.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, crisp clean linework, flat cel-shading, strictly zero neon glow.\n"
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
    print("Starting generation for 45° (ref: [0°, 90°]) and 135° (ref: [0°, 180°]) with stagger...", flush=True)
    results = []
    async with aiohttp.ClientSession() as session:
        # Generate 45 candidates
        t_45_1 = await generate_cand(session, "angle_45_dual_1", PROMPT_45, [mid_0, mid_90])
        await asyncio.sleep(2)
        t_45_2 = await generate_cand(session, "angle_45_dual_2", PROMPT_45, [mid_0, mid_90])
        await asyncio.sleep(2)
        
        # Generate 135 candidates
        t_135_1 = await generate_cand(session, "angle_135_dual_1", PROMPT_135, [mid_0, mid_180])
        await asyncio.sleep(2)
        t_135_2 = await generate_cand(session, "angle_135_dual_2", PROMPT_135, [mid_0, mid_180])
        
        results = [t_45_1, t_45_2, t_135_1, t_135_2]
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "stage2_p2_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Finished 45° and 135° generation:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

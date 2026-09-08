import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "79a7e17f-ebe3-4f0d-8c85-f270e4c03a7d"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tieu-dat-than"

mid_0 = "856d88a1-764e-4a3b-b46f-501e24d415e6"
mid_90 = "a89bf807-02cd-416c-bc3a-3ba0e40daf02"
mid_180 = "c0661381-f281-4d70-b879-fba0cad03995"

PROMPT_45 = (
    "2D Xianxia anime chibi character sprite — TRUE 45-DEGREE THREE-QUARTER VIEW.\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate exactly halfway between Reference 0° (front view) and Reference 90° (lateral side profile).\n"
    "CRITICAL ROTATED TORSO & SHOULDERS: The character's entire upper body, torso, chest, and hips are ROTATED EXACTLY 45 DEGREES to the left (facing 10:30 o'clock direction). "
    "The chest plane is visibly angled diagonally at 45 degrees toward the left, NOT facing front. "
    "The character's left shoulder is clearly positioned forward in the foreground; "
    "the right shoulder is positioned further back in depth and recessed behind the neck. "
    "The diagonal V-neck collar lapel crosses cleanly from right to left across the angled chest in 3/4 perspective. "
    "Both feet are planted and point diagonally toward the left (10 o'clock direction).\n"
    "HAIRSTYLE & IDENTITY: Keep 100% identical hairstyle from references: black hair styled into high topknot with delicate silver jade crown and white silk ribbon tails, "
    "with long straight black hair flowing down the back.\n"
    "COSTUME: Exact same deep royal azure silk martial robe over crisp white inner robe with subtle silver cloud embroidery along lapels and sleeve cuffs, "
    "dark navy-cyan silk waist sash tied neatly with circular white jade medallion, white loose martial trousers, and flat black cloth boots with white soles.\n"
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
    "Keep 100% identical costume and hair: high topknot with silver jade crown and white ribbons seen in 3/4 rear angle, "
    "long black hair flowing down the diagonal back, exact same deep royal azure robe with silver cloud embroidery, "
    "rear sash knot and ribbons matching reference 180° perfectly, loose white trousers, and flat black cloth boots.\n"
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
                    await asyncio.sleep(3)
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
            await asyncio.sleep(3)
    return name, None, None

async def main():
    print("Starting 45° (ref: [0°, 90°]) and 135° (ref: [0°, 180°]) parallel generation...", flush=True)
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "angle_45_dual_1", PROMPT_45, [mid_0, mid_90])
        t2 = generate_cand(session, "angle_45_dual_2", PROMPT_45, [mid_0, mid_90])
        t3 = generate_cand(session, "angle_135_dual_1", PROMPT_135, [mid_0, mid_180])
        t4 = generate_cand(session, "angle_135_dual_2", PROMPT_135, [mid_0, mid_180])
        results = await asyncio.gather(t1, t2, t3, t4)
    print("Finished parallel generation:", results, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

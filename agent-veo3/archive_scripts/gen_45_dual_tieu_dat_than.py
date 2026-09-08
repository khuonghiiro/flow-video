import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "79a7e17f-ebe3-4f0d-8c85-f270e4c03a7d"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tieu-dat-than"

PROMPT_45_DUAL = (
    "2D Xianxia anime chibi character sprite — TRUE 45-DEGREE THREE-QUARTER VIEW.\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate exactly halfway between Reference 0° (front view) and Reference 90° (pure side profile).\n"
    "CRITICAL ROTATED TORSO & SHOULDERS: The character's entire upper body, torso, chest, and hips are ROTATED EXACTLY 45 DEGREES to the left (facing 10:30 o'clock direction). "
    "The chest plane is visibly angled diagonally into depth at 45 degrees, NOT facing camera. "
    "The character's left shoulder is clearly thrust forward into the foreground; "
    "the right shoulder is pulled back deep in perspective and partially occluded. "
    "The diagonal V-neck collar lapel crosses cleanly from right to left across the angled chest. "
    "Both feet are planted and point diagonally toward the left (10 o'clock).\n"
    "HAIRSTYLE & IDENTITY: Keep 100% identical hairstyle from references: black hair styled into high topknot with delicate silver jade crown and white silk ribbon tails, "
    "with long straight black hair flowing down the back.\n"
    "COSTUME: Exact same deep royal azure silk martial robe over crisp white inner robe with subtle silver cloud embroidery along lapels and sleeve cuffs, "
    "dark navy-cyan silk waist sash tied neatly with circular white jade medallion, white loose martial trousers, and flat black cloth boots with white soles.\n"
    "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Completely featureless smooth blank face in 3/4 perspective, perfectly uniform natural fair warm healthy skin tone matching the neck and hands. "
    "STRICTLY ZERO WEAPONS, zero swords, zero instruments, zero props, zero neon glow. "
    "STYLE: Pure flat 2D anime chibi sprite illustration, crisp clean line art, flat cel-shading. "
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

async def run_45_dual(mid_0, mid_90):
    print(f"Starting 45° Dual-Reference Interpolation [0°, 90°]...", flush=True)
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "angle_45_dual_c1", PROMPT_45_DUAL, [mid_0, mid_90])
        t2 = generate_cand(session, "angle_45_dual_c2", PROMPT_45_DUAL, [mid_0, mid_90])
        results = await asyncio.gather(t1, t2)
    print("Completed 45° dual-reference:", results, flush=True)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        mid_0, mid_90 = sys.argv[1], sys.argv[2]
    else:
        with open(os.path.join(OUTPUT_DIR, "character_meta.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            mid_0 = data["angle_0"]["media_id"]
            mid_90 = data["angle_90"]["media_id"]
    asyncio.run(run_45_dual(mid_0, mid_90))

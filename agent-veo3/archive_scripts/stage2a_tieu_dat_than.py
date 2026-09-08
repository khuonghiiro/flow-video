import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "79a7e17f-ebe3-4f0d-8c85-f270e4c03a7d"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tieu-dat-than"

PROMPT_180 = (
    "2D Xianxia anime chibi character sprite — TRUE REAR VIEW (180 DEGREES).\n"
    "Full-body standing pose viewed from directly behind (back turned 100% towards camera, 12 o'clock direction). "
    "Symmetrical standing pose, arms resting naturally at sides, open empty hands, bare hands, strictly zero weapons, zero swords, zero props.\n"
    "BACK OF HEAD & HAIRSTYLE: Back of head visible, neat high topknot with delicate silver jade hair crown (guan) and two white silk ribbon tails fluttering gently, "
    "silky long straight black hair falling down the center of the back.\n"
    "BACK OF COSTUME: Rear view of deep royal azure silk martial robe with delicate silver cloud embroidery along the hem and sleeves, "
    "crisp white under-robe visible, dark navy-cyan silk waist sash tied neatly at the back with hanging sash ends, "
    "white loose martial trousers, and flat black cloth boots with white soles (flat soles, strictly zero heels).\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, harmonious natural colors, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible from head to toe."
)

PROMPT_45 = (
    "2D Xianxia anime chibi character sprite — TRUE 45-DEGREE THREE-QUARTER VIEW.\n"
    "CRITICAL ROTATED TORSO & SHOULDERS: The character's upper body, torso, chest, and hips are ROTATED EXACTLY 45 DEGREES to the left. "
    "The chest plane is visibly angled diagonally at 45 degrees toward the left (10:30 o'clock), NOT facing front. "
    "The character's left shoulder is clearly positioned forward in the foreground; "
    "the right shoulder is positioned further back in depth and recessed. "
    "The diagonal V-neck collar lapel crosses cleanly from right to left in 3/4 perspective. "
    "Both feet are planted and point diagonally toward the left (10 o'clock).\n"
    "HAIRSTYLE & IDENTITY: Keep 100% identical hairstyle from reference: black hair styled into high topknot with delicate silver jade crown and white silk ribbon tails, "
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

async def run_stage2a(media_id_0):
    print("Starting Stage 2A (180° & 45°) for Xiao Yichen...", flush=True)
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "angle_180_c1", PROMPT_180, [media_id_0])
        t2 = generate_cand(session, "angle_180_c2", PROMPT_180, [media_id_0])
        t3 = generate_cand(session, "angle_45_c1", PROMPT_45, [media_id_0])
        t4 = generate_cand(session, "angle_45_c2", PROMPT_45, [media_id_0])
        results = await asyncio.gather(t1, t2, t3, t4)
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "stage2a_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed Stage 2A:", res_dict, flush=True)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mid_0 = sys.argv[1]
    else:
        with open(os.path.join(OUTPUT_DIR, "stage1_results.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            mid_0 = data.get("angle_0_c1", {}).get("media_id")
    asyncio.run(run_stage2a(mid_0))

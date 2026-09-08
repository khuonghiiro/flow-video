import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "79a7e17f-ebe3-4f0d-8c85-f270e4c03a7d"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tieu-dat-than"

PROMPT_90 = (
    "2D Xianxia anime chibi character sprite — TRUE 90-DEGREE SIDE PROFILE VIEW (LEFT FLANK).\n"
    "Full-body character standing strictly in pure side profile facing 9 o'clock direction to the left. "
    "The viewer sees only the left side of the body; the right shoulder, right arm, and right leg are 100% occluded behind the left side.\n"
    "PROFILE OF HEAD & HAIRSTYLE: Side profile of head with blank featureless face, left ear visible. "
    "High topknot with silver jade crown seen in pure side profile, white silk ribbon tail floating behind, "
    "silky long straight black hair cascading down the back.\n"
    "SIDE VIEW OF COSTUME: Left flank profile of deep royal azure silk martial robe, crisp white inner collar wrap visible at the neck, "
    "silver cloud embroidery along sleeve cuff and hem, dark navy-cyan waist sash tied at the left hip with hanging white jade medallion, "
    "loose white martial pants, and flat black cloth boots pointing strictly to the left (9 o'clock, zero heels).\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, crisp clean linework, flat cel-shading, harmonious natural colors, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible."
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
        print(f"Generating {name} (refs: {len(ref_ids)}, attempt {attempt+1})...", flush=True)
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

async def run_stage2b(mid_0, mid_45, mid_180):
    print("Starting Stage 2B (90° & 135°) for Xiao Yichen...", flush=True)
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "angle_90_c1", PROMPT_90, [mid_0, mid_45])
        t2 = generate_cand(session, "angle_90_c2", PROMPT_90, [mid_0, mid_45])
        t3 = generate_cand(session, "angle_135_c1", PROMPT_135, [mid_0, mid_180])
        t4 = generate_cand(session, "angle_135_c2", PROMPT_135, [mid_0, mid_180])
        results = await asyncio.gather(t1, t2, t3, t4)
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "stage2b_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed Stage 2B:", res_dict, flush=True)

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        mid_0, mid_45, mid_180 = sys.argv[1], sys.argv[2], sys.argv[3]
    else:
        with open(os.path.join(OUTPUT_DIR, "character_meta.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            mid_0 = data["angle_0"]["media_id"]
            mid_45 = data["angle_45"]["media_id"]
            mid_180 = data["angle_180"]["media_id"]
    asyncio.run(run_stage2b(mid_0, mid_45, mid_180))

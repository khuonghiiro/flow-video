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
    print("Starting 90 degree side profile generation...", flush=True)
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "angle_90_c1", PROMPT_90, [mid_0])
        t2 = generate_cand(session, "angle_90_c2", PROMPT_90, [mid_0])
        results = await asyncio.gather(t1, t2)
    print("Finished 90 degree generation:", results, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

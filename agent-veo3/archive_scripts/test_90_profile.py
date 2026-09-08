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

PROMPT_90_AGGRESSIVE = (
    "2D Xianxia anime chibi character sprite — PURE 90-DEGREE LATERAL SIDE PROFILE VIEW (LEFT FLANK PROFILE).\n"
    "CAMERA & ORIENTATION: Strictly lateral side profile silhouette, facing exactly 9 o'clock (west) direction. "
    "CRITICAL: STRICTLY FORBIDDEN to face the camera. ZERO front torso visible. ZERO three-quarter view. "
    "The body is seen 100% from the side flank. Only the left shoulder, left arm, left hip, and left leg are visible in the foreground. "
    "The right shoulder, right arm, right leg, and entire chest front are 100% HIDDEN AND OCCLUDED behind the left side silhouette.\n"
    "HEAD & HAIRSTYLE PROFILE: Pure side profile of head facing left (9 o'clock), blank featureless face profile, left ear clearly visible. "
    "High topknot with silver jade hair crown seen in side profile, white silk ribbon tail floating behind, "
    "long black hair cascading down the back edge of the robe.\n"
    "SIDE COSTUME: Left flank profile of deep royal azure silk martial robe, silver cloud embroidery along sleeve cuff and hem, "
    "dark navy-cyan silk waist sash tied at the left hip with hanging white jade medallion, "
    "loose white martial pants, and flat black cloth boots pointing strictly left (9 o'clock, zero heels).\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shading, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible."
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
        print(f"Generating {name} (refs: {len(ref_ids) if ref_ids else 0}, attempt {attempt+1})...", flush=True)
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
    print("Testing 90-degree profile generation...", flush=True)
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "test_90_with_ref_1", PROMPT_90_AGGRESSIVE, [mid_0])
        t2 = generate_cand(session, "test_90_with_ref_2", PROMPT_90_AGGRESSIVE, [mid_0])
        t3 = generate_cand(session, "test_90_no_ref", PROMPT_90_AGGRESSIVE, None)
        results = await asyncio.gather(t1, t2, t3)
    print("Test finished:", results, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

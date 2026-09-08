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

PROMPT_180 = (
    "2D Xianxia anime chibi character sprite — TRUE 180-DEGREE FULL REAR VIEW.\n"
    "Full-body standing pose viewed from directly behind (back turned 100% towards camera, 12 o'clock direction). "
    "Symmetrical standing pose, arms resting naturally at sides, open empty hands, bare hands, strictly zero weapons, zero props.\n"
    "BACK OF HEAD & HAIRSTYLE: Back of head visible, neat high topknot with delicate silver hairpin, "
    "silky long straight black hair falling straight down the center of the back.\n"
    "BACK OF COSTUME & WAIST BELT: Rear view of silvery moon-grey silk daoist martial robe with delicate silver cloud embroidery along the hem and sleeves. "
    "CRITICAL WAIST BELT LOGIC: Broad black-and-silver waist belt wraps smoothly and flatly around the lower back. "
    "STRICTLY CONTINUOUS FLAT BELT BAND AROUND BACK WITH ZERO BOW, ZERO RIBBON KNOT, ZERO DECORATIVE TIES BEHIND. Completely smooth flat belt at rear. "
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Outer robe and hems hang straight down naturally under calm gravity. Strictly NO wind blowing, NO billowing fabric, NO flapping hems, NO flying coat tails. "
    "Loose white trousers, and flat black cloth boots with white soles (flat soles, strictly zero heels, both heels facing camera symmetrically).\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible."
)

PROMPT_90 = (
    "2D Xianxia anime chibi character sprite — PURE 90-DEGREE LATERAL SIDE PROFILE VIEW (LEFT FLANK PROFILE).\n"
    "CAMERA & ORIENTATION: Strictly lateral side profile silhouette, facing exactly 9 o'clock (west) direction to the left. "
    "CRITICAL: STRICTLY FORBIDDEN to face camera. ZERO front torso visible. ZERO three-quarter view. "
    "The body is seen 100% from the side flank. Only the left shoulder, left arm, left hip, and left leg are visible in the foreground. "
    "The right shoulder, right arm, right leg, and entire chest front are 100% COMPLETELY HIDDEN AND OCCLUDED behind the left flank.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: The silvery moon-grey daoist robe and sleeves hang straight down vertically along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO COAT TAILS FLYING BACKWARD, NO FLAPPING HEMS. Calm static fabric drape.\n"
    "HEAD & HAIRSTYLE PROFILE: Pure side profile of head facing left (9 o'clock), blank featureless face profile, left ear clearly visible. "
    "High topknot with silver hairpin seen in side profile, long black hair cascading straight down the back edge of the robe.\n"
    "SIDE COSTUME & BELT: Left flank profile of silvery moon-grey robe, delicate silver cloud embroidery along sleeve cuff and hem, "
    "broad black-and-silver waist belt seen in profile, loose white martial pants, and flat black cloth boots pointing strictly left (9 o'clock, zero heels).\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shading, strictly zero neon glow.\n"
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
    print("Starting generation for 180° and 90° (with 2s stagger)...", flush=True)
    results = []
    async with aiohttp.ClientSession() as session:
        # Generate 180 candidates
        t_180_1 = await generate_cand(session, "angle_180_c1", PROMPT_180, [mid_0])
        await asyncio.sleep(2)
        t_180_2 = await generate_cand(session, "angle_180_c2", PROMPT_180, [mid_0])
        await asyncio.sleep(2)
        
        # Generate 90 candidates
        t_90_1 = await generate_cand(session, "angle_90_c1", PROMPT_90, [mid_0])
        await asyncio.sleep(2)
        t_90_2 = await generate_cand(session, "angle_90_c2", PROMPT_90, [mid_0])
        
        results = [t_180_1, t_180_2, t_90_1, t_90_2]
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "stage2_p1_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Finished 180° and 90° generation:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

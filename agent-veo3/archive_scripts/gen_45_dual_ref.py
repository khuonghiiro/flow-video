import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "29951668-e794-44cb-81e6-dfa24338fc53"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tham-nhuoc-lan"

media_id_0 = "7e567363-3e90-4e9a-a51b-eb9e0748e206"
media_id_90 = "d8dec0a1-bf89-4d9e-9ae9-246fc247e91d"

PROMPT_45_STRONG = (
    "2D Xianxia anime chibi character sprite — DYNAMIC THREE-QUARTER VIEW (TRUE 45-DEGREE ROTATION).\n"
    "CRITICAL TORSO AND SHOULDER POSE: The entire body is rotated 45 degrees to the left (facing 10:30 o'clock). "
    "The shoulders are NOT horizontal and the chest is NOT facing the camera. "
    "The torso is clearly angled diagonally: the character's left shoulder is forward in the foreground, "
    "while the right shoulder is pulled back deep in perspective and partially hidden. "
    "The chest plane and collar V-lapel are seen from a distinct 3/4 diagonal perspective. "
    "Both feet are staggered and planted pointing diagonally at 45 degrees (10 o'clock).\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate halfway between Reference 0° (front) and Reference 90° (profile). "
    "Keep 100% identical costume: seafoam-jade silk robe with fine silver orchid embroidery, white inner robe, "
    "emerald-green waist sash, dark jade hair in twin butterfly looped buns with dangling silver tassels, "
    "and flat white cloth shoes.\n"
    "BLANK FACELESS HEAD & NATURAL SKIN: Smooth featureless blank face in 3/4 perspective matching neck skin tone (warm fair peach skin). "
    "STRICTLY ZERO WEAPONS, zero swords, zero instruments, zero props, zero neon glow. "
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean lines, flat cel-shading. "
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
        print(f"🚀 Generating {name} (refs: {len(ref_ids)}, attempt {attempt+1})...")
        try:
            async with session.post(url, json=body, timeout=120) as resp:
                data = await resp.json()
                media_list = data.get("media", [])
                if not media_list:
                    print(f"❌ {name} fail: {data}")
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
                    print(f"✅ {name} done! Media ID: {mid}, Size: {os.path.getsize(target_file)}")
                    return name, mid, target_file
                elif "image" in m and "encodedImage" in m["image"]:
                    import base64
                    with open(target_file, "wb") as f:
                        f.write(base64.b64decode(m["image"]["encodedImage"]))
                    print(f"✅ {name} done (b64)! Media ID: {mid}, Size: {os.path.getsize(target_file)}")
                    return name, mid, target_file
        except Exception as e:
            print(f"⚠️ {name} error: {e}")
            await asyncio.sleep(3)
    return name, None, None

async def main():
    print("🔥 Starting Dual-Reference 45° Generation [0°, 90°]...")
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "angle_45_rot_1", PROMPT_45_STRONG, [media_id_0, media_id_90])
        t2 = generate_cand(session, "angle_45_rot_2", PROMPT_45_STRONG, [media_id_0, media_id_90])
        results = await asyncio.gather(t1, t2)
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "results_45_rot.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("✅ Completed 45° rotation tests:", res_dict)

if __name__ == "__main__":
    asyncio.run(main())

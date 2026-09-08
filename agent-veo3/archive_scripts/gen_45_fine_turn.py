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

PROMPT_45_TURN = (
    "2D Xianxia anime chibi character sprite — TRUE 45-DEGREE THREE-QUARTER VIEW.\n"
    "CRITICAL ROTATED TORSO & SHOULDERS: The character's upper body, torso, chest, and hips are ROTATED EXACTLY 45 DEGREES to the left. "
    "The chest plane is visibly angled diagonally at 45 degrees toward the left (10:30 o'clock), NOT facing front. "
    "The character's left shoulder is clearly positioned forward in the foreground; "
    "the right shoulder is positioned further back in depth and recessed. "
    "The diagonal V-neck collar lapel crosses cleanly from right to left in 3/4 perspective. "
    "Both feet are planted and point diagonally toward the left (10 o'clock).\n"
    "HAIRSTYLE & IDENTITY: Keep 100% identical hairstyle from reference: black hair styled into TWIN BUTTERFLY LOOPED BUNS on top (both buns visible in 3/4 angle, adorned with white orchid blossoms and light mint ribbons), with long straight black hair flowing down the back.\n"
    "COSTUME: Exact same pastel seafoam-jade outer robe with delicate silver orchid floral embroidery along the lapels and sleeves, crisp white inner robe, emerald-green waist sash tied with jade ring pendant, white pleated floor skirt, and flat white embroidered cloth shoes.\n"
    "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Completely featureless smooth blank face in 3/4 perspective, perfectly uniform natural fair peach skin tone matching the neck and hands. "
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

async def main():
    print("Starting fine-tuned 45 degree shoulder/torso generation...", flush=True)
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "angle_45_turn_1", PROMPT_45_TURN, [media_id_0, media_id_90])
        t2 = generate_cand(session, "angle_45_turn_2", PROMPT_45_TURN, [media_id_0, media_id_90])
        results = await asyncio.gather(t1, t2)
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "results_45_turn.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed fine-tuned 45:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

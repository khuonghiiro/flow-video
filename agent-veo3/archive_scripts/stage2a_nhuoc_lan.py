import asyncio, aiohttp, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "29951668-e794-44cb-81e6-dfa24338fc53"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tham-nhuoc-lan"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(os.path.join(OUTPUT_DIR, "character_meta.json"), "r", encoding="utf-8") as f:
    meta = json.load(f)
media_id_0 = meta["angle_0"]["media_id"]
print(f"Loaded media_id_0: {media_id_0}")

PROMPT_45 = (
    "2D Xianxia anime chibi character sprite — TRUE DEEP 45-DEGREE THREE-QUARTER ISOMETRIC VIEW.\n"
    "POSE & CAMERA: Character body, torso, chest, and feet are turned 45 degrees to the left (facing diagonal 10 o'clock direction). "
    "CRITICAL: STRICTLY FORBIDDEN to face camera directly. ZERO direct front view. "
    "ASYMMETRICAL 3/4 DEPTH POSE: Left foot and left shoulder are stepped forward in the foreground. "
    "Right foot, right shoulder, and right sleeve placed backward in depth behind the body. "
    "Chest plane visibly rotated 45 degrees diagonally away from camera. "
    "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Completely blank smooth featureless face turned 45 degrees to the left showing three-quarter facial contour and left ear (NO eyes, NO nose, NO mouth). Facial skin tone seamlessly matches neck and hands with fair warm peach skin. Strictly ZERO shiny white enamel mask. "
    "CRITICAL — ZERO WEAPONS OR PROPS: Character carries NO weapons, NO swords, NO props. Both hands empty. "
    "LIGHTING: Natural clean flat cel-shading, strictly ZERO neon lighting, ZERO glowing rim bleed. "
    "IDENTITY LOCK: Match 0° reference: Thẩm Nhược Lan, raven-black hair with twin butterfly-loop buns, white orchid hairpins, pale celadon ribbons, seafoam-jade robe with silver orchid embroidery, white inner robe, sash with circular jade pendant, flat white orchid shoes (CRITICAL: STRICTLY FLAT, ZERO HEELS). "
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
)

PROMPT_180 = (
    "2D Xianxia anime chibi character sprite — TRUE 180-DEGREE FULL REAR VIEW.\n"
    "CAMERA & POSE: Character stands with spine vertical facing 100% DIRECTLY AWAY from camera (180° back view). "
    "CRITICAL: Symmetrical back view. Full back of raven-black hair cascading down, twin butterfly hair buns visible from behind, white orchid hairpins, pale celadon ribbons, symmetrical back of seafoam-jade robe with silver frost embroidery, waist sash bow tied at back. "
    "Both heels facing camera, feet pointing away symmetrically. "
    "CRITICAL — ZERO WEAPONS OR PROPS: NO swords on back, NO weapons, NO props. Pure clean robe back. "
    "SHOES: Symmetrical flat white cloth shoes (CRITICAL: STRICTLY FLAT, ZERO HEELS). "
    "LIGHTING: Natural clean flat colors, strictly ZERO neon lighting. "
    "IDENTITY LOCK: Match 0° reference character costume colors, robe design, flat shoes. "
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
)

async def generate_cand(session, name, prompt):
    url = "http://127.0.0.1:8100/api/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "character_media_ids": [media_id_0]
    }
    
    for attempt in range(4):
        print(f"🚀 Bắn request sinh {name} (attempt {attempt+1})...")
        try:
            async with session.post(url, json=body, timeout=120) as resp:
                data = await resp.json()
                if "detail" in data and "Extension not connected" in str(data["detail"]):
                    print(f"⏳ {name}: Extension đang kết nối lại, đợi 3s...")
                    await asyncio.sleep(3)
                    continue
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
                    print(f"✅ {name} hoàn tất! Media ID: {mid}, Size: {os.path.getsize(target_file)}")
                    return name, mid, target_file
                elif "image" in m and "encodedImage" in m["image"]:
                    import base64
                    with open(target_file, "wb") as f:
                        f.write(base64.b64decode(m["image"]["encodedImage"]))
                    print(f"✅ {name} hoàn tất (b64)! Media ID: {mid}, Size: {os.path.getsize(target_file)}")
                    return name, mid, target_file
        except Exception as e:
            print(f"⚠️ {name} error: {e}")
            await asyncio.sleep(3)
    return name, None, None

async def main():
    print("🔥 Bắt đầu Pha 2A: Sinh 45° và 180° (4 requests song song)...")
    tasks = []
    async with aiohttp.ClientSession() as session:
        tasks.append(generate_cand(session, "angle_45_c1", PROMPT_45))
        tasks.append(generate_cand(session, "angle_45_c2", PROMPT_45))
        tasks.append(generate_cand(session, "angle_180_c1", PROMPT_180))
        tasks.append(generate_cand(session, "angle_180_c2", PROMPT_180))
        results = await asyncio.gather(*tasks)
    
    with open(os.path.join(OUTPUT_DIR, "phase2a_results.json"), "w", encoding="utf-8") as f:
        json.dump({name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}, f, indent=2, ensure_ascii=False)
    print("✅ Hoàn tất Pha 2A!")

if __name__ == "__main__":
    asyncio.run(main())

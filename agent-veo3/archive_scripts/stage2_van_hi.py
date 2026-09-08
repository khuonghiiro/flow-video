import asyncio, aiohttp, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "698fe101-ecbe-4102-8474-e27c1d350643"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\van-hi"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(os.path.join(OUTPUT_DIR, "character_meta.json"), "r", encoding="utf-8") as f:
    meta = json.load(f)
media_id_0 = meta["angle_0"]["media_id"]
print(f"Loaded media_id_0: {media_id_0}")

ANGLE_PROMPTS = {
    "45": (
        "2D Xianxia anime chibi character sprite — TRUE DEEP 45-DEGREE THREE-QUARTER ISOMETRIC VIEW.\n"
        "POSE & CAMERA: Character body, torso, chest, and feet are turned 45 degrees to the left (facing diagonal 10 o'clock direction). "
        "CRITICAL: STRICTLY FORBIDDEN to face camera directly. ZERO direct front view. "
        "ASYMMETRICAL 3/4 DEPTH POSE: Left foot and left shoulder are stepped forward in the foreground. "
        "Right foot, right shoulder, and right sleeve placed backward in depth behind the body. "
        "Chest plane visibly rotated 45 degrees diagonally away from camera. "
        "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Completely blank smooth featureless face turned 45 degrees to the left showing three-quarter facial contour and left ear (NO eyes, NO nose, NO mouth). Facial skin tone seamlessly matches neck and hands with fair warm peach skin. Strictly ZERO shiny white enamel mask. "
        "CRITICAL — ZERO WEAPONS OR PROPS: Character carries NO weapons, NO swords, NO props. Both hands empty. "
        "LIGHTING: Natural clean flat cel-shading, strictly ZERO neon lighting, ZERO glowing rim bleed. "
        "IDENTITY LOCK: Match 0° reference: Vân Hi, long silky flowing raven-black hair half-up bun with silver lotus hairpin and pale azure ribbons, moonlit-white daoist robe with wide sleeves, soft mist-blue overskirt, celadon silk sash with jade pendant, flat ivory lotus cloth shoes (CRITICAL: STRICTLY FLAT, ZERO HEELS). "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "90": (
        "2D Xianxia anime chibi character sprite — TRUE 90-DEGREE PURE SIDE PROFILE VIEW.\n"
        "CAMERA & POSE: Character stands in strict 90-degree left side silhouette (facing exactly 9 o'clock direction). "
        "PURE LATERAL FLANK VIEW: Only left side of character is visible: left side of head, left shoulder, left wide pagoda sleeve, left side of moonlit-white robe and mist-blue overskirt, left hip, left leg, and left flat lotus shoe pointing directly to 9 o'clock. "
        "Right arm, right shoulder, and right leg are 100% occluded directly behind the body and invisible. "
        "CRITICAL: STRICTLY ZERO FRONT VIEW, ZERO FRONT CHEST. Pure flank side silhouette. "
        "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Pure smooth blank face in left side profile outline (NO eyes, NO nose, NO mouth). Skin tone matches neck (fair warm peach skin). Strictly ZERO shiny white mask. "
        "CRITICAL — ZERO WEAPONS OR PROPS: NO weapons, NO swords on back or waist, NO props. Both hands empty. "
        "SHOES: Flat ivory lotus cloth shoe (CRITICAL: STRICTLY FLAT, ZERO HEELS). "
        "LIGHTING: Natural flat cel-shading, strictly ZERO neon lighting, ZERO glowing rim bleed. "
        "IDENTITY LOCK: Match 0° reference character costume colors, black hair with silver hairpin and azure ribbons. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, bold clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "135": (
        "2D Xianxia anime chibi character sprite — TRUE 135-DEGREE BACK-LEFT THREE-QUARTER PERSPECTIVE.\n"
        "CAMERA & POSE: Character viewed from behind-left at 135-degree angle (facing diagonal 8 o'clock away from camera). "
        "CRITICAL: Full view of back of head, raven-black hair with silver lotus hairpin and twin pale azure silk ribbons, back of moonlit-white robe and mist-blue overskirt, celadon sash ribbon bow visible from behind. "
        "Left shoulder and left heel visible in foreground; right shoulder angled away in depth. "
        "CRITICAL — ZERO WEAPONS OR PROPS: NO swords on back or waist, NO weapons, NO props. Clean back of robe. "
        "SHOES: Flat ivory lotus cloth shoes (CRITICAL: STRICTLY FLAT, ZERO HEELS, NO HIGH HEELS). "
        "LIGHTING & SKIN: Natural skin tone seamlessly matching. Strictly ZERO neon glow or reflections. "
        "IDENTITY LOCK: Match 0° reference character costume colors, fabrics, and flat shoes. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "180": (
        "2D Xianxia anime chibi character sprite — TRUE 180-DEGREE FULL REAR VIEW.\n"
        "CAMERA & POSE: Character stands with spine vertical facing 100% DIRECTLY AWAY from camera (180° back view). "
        "CRITICAL: Symmetrical back view. Full back of flowing silky raven-black hair cascading down, silver lotus hairpin, azure silk ribbons, symmetrical back of moonlit-white daoist robe, celadon waist sash bow. "
        "Both heels facing camera, feet pointing away symmetrically. "
        "CRITICAL — ZERO WEAPONS OR PROPS: NO swords on back, NO weapons, NO props. Pure clean robe back. "
        "SHOES: Symmetrical flat ivory lotus cloth shoes (CRITICAL: STRICTLY FLAT, ZERO HEELS). "
        "LIGHTING: Natural clean flat colors, strictly ZERO neon lighting. "
        "IDENTITY LOCK: Match 0° reference character costume colors, white robe, mist-blue accents. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
}

async def generate_candidate(session, angle, cand_idx, prompt, media_id_0):
    url = "http://127.0.0.1:8100/api/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "character_media_ids": [media_id_0]
    }
    cand_name = f"angle_{angle}_c{cand_idx}"
    
    for attempt in range(4):
        print(f"🚀 [{attempt+1}/4] Bắn request sinh {cand_name} (angle={angle}°)...")
        try:
            async with session.post(url, json=body, timeout=120) as resp:
                data = await resp.json()
                if "detail" in data and "Extension not connected" in str(data["detail"]):
                    print(f"⏳ {cand_name}: Extension đang kết nối lại, đợi 3s...")
                    await asyncio.sleep(3)
                    continue
                media_list = data.get("media", [])
                if not media_list:
                    print(f"❌ {cand_name} fail: {data}")
                    if attempt < 3:
                        await asyncio.sleep(3)
                        continue
                    return cand_name, None, None
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
                
                target_file = os.path.join(OUTPUT_DIR, f"{cand_name}.png")
                if img_url:
                    async with session.get(img_url) as img_resp:
                        content = await img_resp.read()
                        with open(target_file, "wb") as f:
                            f.write(content)
                    print(f"✅ {cand_name} hoàn tất! Media ID: {mid}, Size: {os.path.getsize(target_file)}")
                elif "image" in m and "encodedImage" in m["image"]:
                    import base64
                    with open(target_file, "wb") as f:
                        f.write(base64.b64decode(m["image"]["encodedImage"]))
                    print(f"✅ {cand_name} hoàn tất (base64)! Media ID: {mid}, Size: {os.path.getsize(target_file)}")
                else:
                    print(f"⚠️ {cand_name} không tìm thấy ảnh:", m)
                    return cand_name, mid, None
                return cand_name, mid, target_file
        except Exception as e:
            print(f"⚠️ {cand_name} attempt {attempt+1} error: {e}")
            await asyncio.sleep(3)
    return cand_name, None, None

async def main():
    print(f"🔥 Bắt đầu sinh 8 candidates song song cho 4 góc (45°, 90°, 135°, 180°)...")
    tasks = []
    async with aiohttp.ClientSession() as session:
        for angle in ["45", "90", "135", "180"]:
            p = ANGLE_PROMPTS[angle]
            tasks.append(generate_candidate(session, angle, 1, p, media_id_0))
            tasks.append(generate_candidate(session, angle, 2, p, media_id_0))
        
        results = await asyncio.gather(*tasks)
        
    summary = {}
    for cand_name, mid, fpath in results:
        summary[cand_name] = {"media_id": mid, "file": fpath}
        print(f"Result: {cand_name} -> {mid} ({fpath})")
        
    with open(os.path.join(OUTPUT_DIR, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("✅ Đã lưu candidates.json!")

if __name__ == "__main__":
    asyncio.run(main())

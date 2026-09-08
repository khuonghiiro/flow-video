import asyncio, aiohttp, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "b1b4897d-a85d-4d97-9736-5ba6b3bf7552"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\vo-tam-tien-nhan"

ANGLE_PROMPTS = {
    "45": (
        "2D Xianxia anime chibi character sprite — TRUE THREE-QUARTER VIEW 45 DEGREES.\n"
        "POSE & CAMERA: Character body and head are turned 45 degrees towards the left (facing diagonal 10 o'clock direction). "
        "CRITICAL: STRICTLY FORBIDDEN to face the camera. ZERO direct front view. "
        "ASYMMETRICAL 3/4 POSE: Left foot and left shoulder step forward into front foreground. "
        "Right foot and right shoulder placed behind in depth. Chest and torso rotated 45 degrees away from camera. "
        "Head turned 45 degrees to the left showing three-quarter jaw contour and left ear contour. "
        "CRITICAL — BLANK FACELESS HEAD: Completely BLANK, SMOOTH, FEATURELESS face surface (NO eyes, NO eyebrows, NO nose, NO mouth). Pure smooth cold white jade porcelain skin. "
        "IDENTITY LOCK: Match 0° reference: Vô Tâm Tiên Nhân, tall athletic male cultivator, long black hair high ponytail tied with red silk cord + azure quartz hairpin, deep night-sky blue daoist robe (#0D47A1) with silver rune borders, front vertical golden embroidery line, ankle-length outer coat with white plum blossoms & silver feather cuffs, pale azure trousers with lavender gradient, golden silk sash belt with central sapphire jade bead and twin golden kirin tassels, FLAT azure cloth boots with glowing cyan energy soles (STRICTLY ZERO HEELS), azure frost sword strapped on back. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "90": (
        "2D Xianxia anime chibi character sprite — TRUE 90-DEGREE PURE SIDE PROFILE.\n"
        "CAMERA & POSE: Character stands in strict left side profile silhouette (facing exactly 9 o'clock direction). "
        "CRITICAL: Pure flank side view. STRICTLY ZERO three-quarter view, ZERO front torso visible. "
        "Only left eye-level profile, left shoulder, left arm, left hip, left leg and left foot visible in the foreground. "
        "Right arm, right shoulder and right leg are occluded 100% directly behind the left side. "
        "Azure frost sword strapped diagonally on back clearly visible from side silhouette angle. "
        "CRITICAL — BLANK FACELESS HEAD: Completely BLANK, SMOOTH, FEATURELESS face profile (NO eyes, NO eyebrows, NO nose, NO mouth). Pure smooth cold white jade porcelain skin. "
        "IDENTITY LOCK: Exact same deep blue robes, silver runes, outer coat, golden sash belt, flat azure cloth boots with glowing cyan soles (ZERO HEELS), long black hair ponytail with red ribbon. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, bold clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "135": (
        "2D Xianxia anime chibi character sprite — TRUE 135-DEGREE BACK-LEFT THREE-QUARTER PERSPECTIVE.\n"
        "CAMERA & POSE: Character viewed from behind-left at a 135-degree angle (facing diagonal 8 o'clock away from camera). "
        "CRITICAL: Full view of back of head, high ponytail tied with red silk cord + azure quartz hairpin, back of shoulders, back of deep blue daoist robe and outer coat with silver crane feathers, full back view of azure frost sword strapped diagonally across spine. "
        "Left shoulder and left heel visible in foreground; right shoulder angled away in depth. "
        "SHOES: Flat cloud-woven azure cloth boots with glowing cyan energy soles (CRITICAL: STRICTLY FLAT, ZERO HEELS, NO HIGH HEELS). "
        "IDENTITY LOCK: Exact same character costume, color scheme, flat shoes, and sword. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "180": (
        "2D Xianxia anime chibi character sprite — TRUE 180-DEGREE FULL REAR VIEW.\n"
        "CAMERA & POSE: Character stands with spine vertical facing 100% DIRECTLY AWAY from camera (180° back view). "
        "CRITICAL: Symmetrical back view. Full back of high ponytail with red silk cord and azure quartz hairpin, symmetrical back of outer coat with silver rune border and plum blossoms, full back of azure frost sword strapped across back. "
        "Both heels facing camera, feet pointing away symmetrically. "
        "SHOES: Symmetrical flat azure cloth boots with soft cyan energy soles (CRITICAL: STRICTLY FLAT, ZERO HEELS). "
        "IDENTITY LOCK: Match 0° reference character costume colors, silver runes, golden belt ribbons. "
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
                    return cand_name, mid, target_file
                elif "image" in m and "encodedImage" in m["image"]:
                    import base64
                    with open(target_file, "wb") as f:
                        f.write(base64.b64decode(m["image"]["encodedImage"]))
                    print(f"✅ {cand_name} hoàn tất từ base64! Media ID: {mid}")
                    return cand_name, mid, target_file
                else:
                    print(f"⚠️ {cand_name} không có URL/base64")
                    return cand_name, mid, None
        except Exception as e:
            print(f"⚠️ Lỗi kết nối {cand_name} (attempt {attempt+1}): {e}")
            if attempt < 3:
                await asyncio.sleep(3)
                continue
            return cand_name, None, None
    return cand_name, None, None

async def main():
    meta_path = os.path.join(OUTPUT_DIR, "character_meta.json")
    if not os.path.exists(meta_path):
        print("Chưa có character_meta.json! Hãy chạy Tầng 1 trước.")
        return
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    mid_0 = meta["angle_0"]["media_id"]
    print(f"Nạp Master Reference media_id_0: {mid_0}")
    
    tasks = []
    conn = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=conn) as session:
        for angle in ["45", "90", "135", "180"]:
            prompt = ANGLE_PROMPTS[angle]
            tasks.append(generate_candidate(session, angle, 1, prompt, mid_0))
            await asyncio.sleep(0.3)
            tasks.append(generate_candidate(session, angle, 2, prompt, mid_0))
            await asyncio.sleep(0.3)
        results = await asyncio.gather(*tasks)
        
    candidates = {}
    for cand_name, mid, fpath in results:
        candidates[cand_name] = {"media_id": mid, "file": fpath}
    with open(os.path.join(OUTPUT_DIR, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)
    print("\n🎉 Đã lưu kết quả 8 ứng viên vào candidates.json!")

if __name__ == "__main__":
    asyncio.run(main())

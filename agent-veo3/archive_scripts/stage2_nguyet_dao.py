import asyncio, aiohttp, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "853ab682-e875-48a8-a652-9d12d85cfa2d"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\nguyet-dao"

ANGLE_PROMPTS = {
    "45": (
        "2D Xianxia anime chibi character sprite — TRUE DEEP 45-DEGREE THREE-QUARTER ISOMETRIC VIEW.\n"
        "POSE & CAMERA: Character body, torso, chest, and feet are turned 45 degrees to the left (facing diagonal 10 o'clock direction). "
        "CRITICAL: STRICTLY FORBIDDEN to face camera directly. ZERO direct front view. "
        "ASYMMETRICAL 3/4 DEPTH POSE: Left foot and left shoulder are stepped forward in the foreground. "
        "Right foot, right shoulder, and right sleeve placed backward in depth behind the body. "
        "Chest plane visibly rotated 45 degrees diagonally away from camera. "
        "BLANK FACELESS HEAD: Completely blank smooth porcelain mannequin head turned 45 degrees to the left showing three-quarter facial contour and left ear (NO eyes, NO nose, NO mouth). "
        "IDENTITY LOCK: Match 0° reference: Băng Nguyệt Tiên Tử (Nguyệt Dao), long flowing silvery-white hair half-up bun with crystal lotus hairpin and twin floating cyan silk ribbons, pure snow-white daoist robe with silver frost patterns, translucent icy cyan slit overskirt, soft lilac sash with crescent moon jade, flat white lotus shoes with glowing cyan energy soles (CRITICAL: STRICTLY FLAT, ZERO HEELS, NO HIGH HEELS), translucent icy crystal sword strapped across back. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "90": (
        "2D Xianxia anime chibi character sprite — TRUE 90-DEGREE PURE SIDE PROFILE VIEW.\n"
        "CAMERA & POSE: Character stands in strict 90-degree left side silhouette (facing exactly 9 o'clock direction). "
        "PURE LATERAL FLANK VIEW: Only left side of character is visible: left side of head, left shoulder, left fairy sleeve, left side of white robe and cyan slit overskirt, left hip, left leg, and left flat lotus shoe pointing directly to 9 o'clock. "
        "Right arm, right shoulder, and right leg are 100% occluded directly behind the body and invisible. "
        "CRITICAL: STRICTLY ZERO FRONT VIEW, ZERO FRONT CHEST. Pure flank side silhouette. "
        "Translucent icy crystal sword strapped on back visible from side profile. Long silvery-white hair and cyan ribbons streaming backward. "
        "BLANK FACELESS HEAD: Pure smooth blank mannequin head in left side profile outline (NO eyes, NO nose, NO mouth). "
        "SHOES: Flat white lotus shoe with glowing cyan energy sole (STRICTLY FLAT, ZERO HEELS). "
        "STYLE: Pure flat 2D anime chibi sprite illustration, bold clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "135": (
        "2D Xianxia anime chibi character sprite — TRUE 135-DEGREE BACK-LEFT THREE-QUARTER PERSPECTIVE.\n"
        "CAMERA & POSE: Character viewed from behind-left at 135-degree angle (facing diagonal 8 o'clock away from camera). "
        "CRITICAL: Full view of back of head, silvery-white hair with crystal lotus hairpin and twin cyan silk ribbons, back of white robe with silver frost embroidery, translucent icy crystal sword strapped diagonally across spine with cyan jade tassel. "
        "Left shoulder and left heel visible in foreground; right shoulder angled away in depth. "
        "SHOES: Flat white lotus cloth shoes with glowing cyan energy soles (CRITICAL: STRICTLY FLAT, ZERO HEELS, NO HIGH HEELS). "
        "IDENTITY LOCK: Match 0° reference character costume colors, slit overskirt, and flat shoes. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "180": (
        "2D Xianxia anime chibi character sprite — TRUE 180-DEGREE FULL REAR VIEW.\n"
        "CAMERA & POSE: Character stands with spine vertical facing 100% DIRECTLY AWAY from camera (180° back view). "
        "CRITICAL: Symmetrical back view. Full back of flowing silvery-white hair cascading down, crystal lotus hairpin, cyan silk ribbons, symmetrical back of white daoist robe with silver frost embroidery, translucent icy crystal sword strapped across back, lilac waist sash bow. "
        "Both heels facing camera, feet pointing away symmetrically. "
        "SHOES: Symmetrical flat white lotus cloth shoes with soft cyan energy soles (CRITICAL: STRICTLY FLAT, ZERO HEELS). "
        "IDENTITY LOCK: Match 0° reference character costume colors, white robe, cyan accents. "
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
            print(f"⚠️ Lỗi {cand_name} (attempt {attempt+1}): {e}")
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

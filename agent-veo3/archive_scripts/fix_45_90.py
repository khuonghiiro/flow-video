import asyncio, aiohttp, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "b1b4897d-a85d-4d97-9736-5ba6b3bf7552"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\vo-tam-tien-nhan"

meta_path = os.path.join(OUTPUT_DIR, "character_meta.json")
with open(meta_path, "r", encoding="utf-8") as f:
    meta = json.load(f)
mid_0 = meta["angle_0"]["media_id"]

PROMPTS = {
    "45": (
        "2D Xianxia anime chibi character sprite — DEEP 45-DEGREE THREE-QUARTER ISOMETRIC ANGLE.\n"
        "CAMERA & PERSPECTIVE: Camera positioned at a 45-degree angle to the left of the character. "
        "Character body, torso, chest, and feet are all turned 45 degrees towards the diagonal left (facing 10 o'clock direction). "
        "ASYMMETRICAL 3/4 DEPTH POSE: Left foot and left shoulder are stepped forward into the foreground. "
        "Right shoulder, right arm, and right leg are placed backward in depth behind the body. "
        "The chest plane is visibly rotated 45 degrees diagonally away from camera. "
        "CRITICAL: STRICTLY FORBIDDEN to face the camera directly. ZERO direct front view. "
        "BLANK FACELESS HEAD: Completely blank smooth porcelain mannequin head turned 45 degrees to the left showing three-quarter facial outline and left ear contour (NO eyes, NO nose, NO mouth). "
        "IDENTITY LOCK: Match reference character: high ponytail with red ribbon, deep night-sky blue daoist robe, white outer coat, flat azure cloth boots with glowing cyan energy soles (STRICTLY FLAT, ZERO HEELS), azure frost sword strapped on back. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "90": (
        "2D Xianxia anime chibi character sprite — TRUE 90-DEGREE PURE SIDE PROFILE VIEW.\n"
        "CAMERA & POSE: Character stands in strict 90-degree left side silhouette (facing exactly 9 o'clock direction). "
        "PURE LATERAL FLANK VIEW: Only the left side of the character is visible: left side of head, left shoulder, left sleeve, left side of outer coat, left hip, left leg, and left flat azure boot pointing directly to the left (9 o'clock). "
        "The right arm, right shoulder, and right leg are 100% occluded directly behind the body and invisible. "
        "CRITICAL: STRICTLY ZERO FRONT VIEW, ZERO FRONT CHEST. Pure side profile silhouette. "
        "Azure frost sword strapped on back visible from the side. High ponytail tied with red ribbon streams backward from the crown. "
        "BLANK FACELESS HEAD: Pure smooth blank mannequin head in left side profile outline (NO eyes, NO nose, NO mouth). "
        "SHOES: Flat azure cloth boot with glowing cyan energy sole (STRICTLY FLAT, ZERO HEELS). "
        "STYLE: Pure flat 2D anime chibi sprite illustration, bold clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    )
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
    print(f"🚀 Bắn request sinh {cand_name} (angle={angle}°)...")
    try:
        async with session.post(url, json=body, timeout=120) as resp:
            data = await resp.json()
            media_list = data.get("media", [])
            if not media_list:
                print(f"❌ {cand_name} fail:", data)
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
    except Exception as e:
        print(f"❌ Lỗi {cand_name}: {e}")
        return cand_name, None, None

async def main():
    tasks = []
    conn = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=conn) as session:
        # Generate c3 and c4 for 45 and 90
        for angle in ["45", "90"]:
            tasks.append(generate_candidate(session, angle, 3, PROMPTS[angle], mid_0))
            await asyncio.sleep(0.3)
            tasks.append(generate_candidate(session, angle, 4, PROMPTS[angle], mid_0))
            await asyncio.sleep(0.3)
        results = await asyncio.gather(*tasks)
    print("Done generating c3, c4 for 45 and 90!")

if __name__ == "__main__":
    asyncio.run(main())

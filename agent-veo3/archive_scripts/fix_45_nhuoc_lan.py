import asyncio, aiohttp, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "29951668-e794-44cb-81e6-dfa24338fc53"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tham-nhuoc-lan"

with open(os.path.join(OUTPUT_DIR, "character_meta.json"), "r", encoding="utf-8") as f:
    meta = json.load(f)
media_id_0 = meta["angle_0"]["media_id"]

PROMPTS = {
    "angle_45_v1": (
        "2D Xianxia anime chibi character sprite — TRUE PRONOUNCED 45-DEGREE THREE-QUARTER VIEW.\n"
        "CRITICAL BODY & SHOULDER ROTATION: The character's entire upper body, shoulders, chest, and hips are ROTATED 45 DEGREES to the left (facing diagonal 10 o'clock direction). "
        "STRICTLY FORBIDDEN to face the camera flatly. ZERO front-facing chest. "
        "ASYMMETRICAL SHOULDER DEPTH: Left shoulder is rotated forward into the foreground; right shoulder is rotated back into deep background. "
        "The chest plane is angled 45 degrees in perspective. The collar opening and waist sash bow are visibly shifted to the left flank, NOT centered. "
        "Left arm and wide sleeve in front, right arm drawn back behind the torso. Left foot stepped forward, right foot behind in 45-degree angle. "
        "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Blank smooth featureless face turned 45 degrees left (NO eyes, NO nose, NO mouth). Warm peach skin matching neck. "
        "IDENTITY LOCK: Match 0° reference: Thẩm Nhược Lan, raven-black hair with twin butterfly-loop buns, white orchid hairpins, pale celadon ribbons, seafoam-jade robe, white inner robe, sash, flat white orchid cloth shoes (STRICTLY FLAT, ZERO HEELS). NO weapons, NO neon. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "angle_45_v2": (
        "2D Xianxia anime chibi character sprite — 45-DEGREE ISOMETRIC THREE-QUARTER ANGLE.\n"
        "TORSO & SHOULDERS ANGLED AT 45 DEGREES: The torso, ribcage, shoulders, and hips are angled 45 degrees away from camera towards the left. "
        "Perspective projection: diagonal chest plane showing side-front contour. Left shoulder closer to viewer, right shoulder further away in perspective. "
        "Sash ornament and robe lapel cross over diagonally to the left. Head turned 45 degrees left. "
        "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Smooth blank face in 3/4 angle, warm peach skin matching neck (NO facial features). "
        "IDENTITY LOCK: Match 0° reference: Thẩm Nhược Lan, seafoam-jade robe, raven-black butterfly hair, flat cloth shoes. Zero weapons, zero neon. "
        "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "angle_45_v3": (
        "2D Xianxia anime chibi character sprite — TRUE DEEP 45-DEGREE ROTATION.\n"
        "FULL TORSO ROTATION: The character is standing turned at a distinct 45-degree angle to the left. "
        "The chest is NOT facing viewer; the chest faces diagonal 10 o'clock. The left side of the torso is prominent, the right side of torso is receding in distance. "
        "Shoulder line is angled steeply at 45 degrees into depth. Left arm hangs forward, right arm partially occluded behind body. Both feet point diagonally left. "
        "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Smooth featureless face turned 45 degrees left, matching neck skin color. "
        "IDENTITY LOCK: Match 0° reference Thẩm Nhược Lan, seafoam jade robes, butterfly buns. Strictly flat shoes, zero weapons, zero neon. "
        "STYLE: Pure flat 2D anime chibi sprite, clean linework, flat cel-shaded colors. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
    "angle_45_v4": (
        "2D Xianxia anime chibi character sprite — EXACT THREE-QUARTER ISOMETRIC VIEW 45 DEGREES.\n"
        "HALFWAY ROTATION BETWEEN 0° FRONT AND 90° PROFILE: Character body, shoulders, chest, and feet are turned exactly 45 degrees. "
        "Clearly visible diagonal shoulder line and tilted chest plane. The robe center seam is shifted significantly to the left side of the silhouette. "
        "Right shoulder and right sleeve are largely hidden in background perspective. Left shoulder and left sleeve in sharp foreground. "
        "BLANK FACELESS HEAD: Smooth blank face turned 45 degrees, matching neck skin tone. "
        "IDENTITY LOCK: Match 0° reference Thẩm Nhược Lan, seafoam jade robe, flat shoes, zero weapons, zero neon. "
        "STYLE: Pure flat 2D anime chibi sprite, clean linework, flat cel-shaded colors. "
        "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
    ),
}

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
    print("🔥 Bắt đầu sinh 4 biến thể góc 45° với ép xoay vai & thân người rõ rệt...")
    tasks = []
    async with aiohttp.ClientSession() as session:
        for name, prompt in PROMPTS.items():
            tasks.append(generate_cand(session, name, prompt))
        results = await asyncio.gather(*tasks)
    
    with open(os.path.join(OUTPUT_DIR, "fix_45_results.json"), "w", encoding="utf-8") as f:
        json.dump({name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}, f, indent=2, ensure_ascii=False)
    print("✅ Hoàn tất sinh 4 biến thể 45°!")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio, aiohttp, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "29951668-e794-44cb-81e6-dfa24338fc53"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tham-nhuoc-lan"

media_id_0 = "7e567363-3e90-4e9a-a51b-eb9e0748e206"
media_id_45 = "a513b91a-57b3-496b-89b9-f3ed3887cad0"
media_id_180 = "d3ce9ec7-89a9-419b-bb57-780a3d3f00d6"

print(f"Pha 2B Reference IDs:")
print(f"  0°  : {media_id_0}")
print(f"  45° : {media_id_45}")
print(f"  180°: {media_id_180}")

# 90° references [0°, 45°]
PROMPT_90 = (
    "2D Xianxia anime chibi character sprite — TRUE 90-DEGREE PURE SIDE PROFILE VIEW.\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate between the 0° front view and the 45° three-quarter view to produce the exact 90° left flank profile. "
    "CAMERA & POSE: Character stands in strict 90-degree left side silhouette (facing exactly 9 o'clock direction). "
    "PURE LATERAL FLANK VIEW: Only left side of character is visible: left side of head, left butterfly bun and hairpin, left shoulder, left sleeve, left side of seafoam-jade robe and white skirt, left hip, left leg, and left flat cloth shoe pointing directly to 9 o'clock. "
    "Right arm, right shoulder, and right leg are 100% occluded directly behind the body and invisible. "
    "CRITICAL: STRICTLY ZERO FRONT VIEW, ZERO FRONT CHEST. Pure flank side silhouette. "
    "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Pure smooth blank face in left side profile outline (NO eyes, NO nose, NO mouth). Skin tone matches neck (fair warm peach skin). Strictly ZERO shiny white mask. "
    "CRITICAL — ZERO WEAPONS OR PROPS: NO weapons, NO swords on back or waist, NO props. Both hands empty. "
    "SHOES: Flat white cloth shoe (CRITICAL: STRICTLY FLAT, ZERO HEELS). "
    "LIGHTING: Natural flat cel-shading, strictly ZERO neon lighting, ZERO glowing rim bleed. "
    "IDENTITY LOCK: Match reference costume colors, raven hair with butterfly bun, pale celadon ribbons. "
    "STYLE: Pure flat 2D anime chibi sprite illustration, bold clean linework, flat cel-shaded coloring. "
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
)

# 135° references [0°, 180°]
PROMPT_135 = (
    "2D Xianxia anime chibi character sprite — TRUE 135-DEGREE BACK-LEFT THREE-QUARTER PERSPECTIVE.\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate between the 0° front reference and the 180° rear reference. Both front dress layers and rear sash bow MUST match reference 0° and reference 180° with 100% continuity. "
    "CAMERA & POSE: Character viewed from behind-left at 135-degree angle (facing diagonal 8 o'clock away from camera). "
    "CRITICAL: Full view of back-left of head, raven-black hair with butterfly bun and white orchid hairpin, back of seafoam-jade robe, green silk sash bow tied at back as shown in 180° reference. "
    "Left shoulder and left heel visible in foreground; right shoulder angled away in depth. "
    "CRITICAL — ZERO WEAPONS OR PROPS: NO swords on back or waist, NO weapons, NO props. Clean back of robe. "
    "SHOES: Flat white cloth shoes (CRITICAL: STRICTLY FLAT, ZERO HEELS, NO HIGH HEELS). "
    "LIGHTING & SKIN: Natural skin tone seamlessly matching. Strictly ZERO neon glow or reflections. "
    "IDENTITY LOCK: Exact same costume fabrics, rear sash ribbon bow, and flat shoes as 180° reference. "
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean linework, flat cel-shaded coloring. "
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
    
    for attempt in range(4):
        print(f"🚀 Bắn request sinh {name} (refs: {len(ref_ids)}, attempt {attempt+1})...")
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
    print("🔥 Bắt đầu Pha 2B: Sinh 90° (ref: [0°, 45°]) và 135° (ref: [0°, 180°]) song song...")
    tasks = []
    async with aiohttp.ClientSession() as session:
        # 90° candidates (2 candidates) referencing [media_id_0, media_id_45]
        tasks.append(generate_cand(session, "angle_90_c1", PROMPT_90, [media_id_0, media_id_45]))
        tasks.append(generate_cand(session, "angle_90_c2", PROMPT_90, [media_id_0, media_id_45]))
        
        # 135° candidates (2 candidates) referencing [media_id_0, media_id_180]
        tasks.append(generate_cand(session, "angle_135_c1", PROMPT_135, [media_id_0, media_id_180]))
        tasks.append(generate_cand(session, "angle_135_c2", PROMPT_135, [media_id_0, media_id_180]))
        
        results = await asyncio.gather(*tasks)
        
    with open(os.path.join(OUTPUT_DIR, "phase2b_results.json"), "w", encoding="utf-8") as f:
        json.dump({name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}, f, indent=2, ensure_ascii=False)
    print("✅ Hoàn tất Pha 2B!")

if __name__ == "__main__":
    asyncio.run(main())

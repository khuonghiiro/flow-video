import urllib.request, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "853ab682-e875-48a8-a652-9d12d85cfa2d"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\nguyet-dao"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PROMPT_0 = (
    "2D Xianxia anime chibi character sprite — TRUE DIRECT 0-DEGREE FRONT VIEW.\n"
    "Full body standing centered, facing directly at camera (12 o'clock).\n"
    "CRITICAL — BLANK FACELESS HEAD: Completely BLANK, SMOOTH, FEATURELESS face surface (NO eyes, NO eyebrows, NO nose, NO mouth). Pure smooth porcelain skin with soft luminous ethereal white jade glow.\n"
    "CHARACTER: Băng Nguyệt Tiên Tử — Nguyệt Dao (Lunar Frost Fairy), female immortal sword cultivator, 19-20 years old appearance, slender graceful ethereal physique (167cm, 47kg), elegant poised immortal fairy presence.\n"
    "HAIRSTYLE: Silky long flowing moonlight silvery-white hair tied into an elegant half-up bun with a crystal lotus hairpin and twin floating translucent cyan silk ribbons.\n"
    "COSTUME DETAILS:\n"
    "- Pure snow-white ethereal daoist silk robe embroidered with delicate silver frost and snowflake patterns.\n"
    "- Layered translucent pale icy cyan slit overskirt with flowing side slits.\n"
    "- Soft lavender lilac waist sash belt with a glowing crescent moon jade pendant.\n"
    "- Delicate silver-trimmed flowing fairy sleeves.\n"
    "- SHOES: Soft white embroidered lotus cloth shoes with faint glowing icy cyan energy soles (CRITICAL: STRICTLY FLAT, ZERO HEELS, NO HIGH HEELS).\n"
    "WEAPON: Translucent icy crystal sword ('Huyền Băng Linh Kiếm') strapped diagonally across back, crystal hilt and cyan jade tassel visible behind shoulder.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, bold clean linework, flat cel-shaded coloring.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible from head to feet."
)

print("🚀 Bắt đầu sinh ảnh 0° (Master Root) cho Nguyệt Dao...")
print("Project ID:", PROJECT_ID)

req = urllib.request.Request(
    "http://127.0.0.1:8100/api/flow/generate-image",
    data=json.dumps({
        "prompt": PROMPT_0,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO"
    }).encode("utf-8"),
    headers={"Content-Type": "application/json", "Accept": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=120) as res:
        res_data = json.loads(res.read())
        media_list = res_data.get("media", [])
        if not media_list:
            print("Raw response:", json.dumps(res_data, indent=2))
            sys.exit(1)
            
        m = media_list[0]
        media_id = m.get("name")
        print("✅ Media ID:", media_id)
        
        gen_img = m.get("image", {}).get("generatedImage", {})
        img_url = (
            m.get("fifeUrl")
            or m.get("servingUri")
            or gen_img.get("fifeUrl")
            or gen_img.get("servingUri")
            or m.get("image", {}).get("fifeUrl")
            or m.get("image", {}).get("servingUri")
        )
            
        print("Image URL:", img_url)
        
        target_path = os.path.join(OUTPUT_DIR, "angle_0.png")
        if img_url:
            print("Tải ảnh về", target_path)
            urllib.request.urlretrieve(img_url, target_path)
            print("✅ Đã lưu angle_0.png! Size:", os.path.getsize(target_path))
        elif "image" in m and "encodedImage" in m["image"]:
            import base64
            with open(target_path, "wb") as f:
                f.write(base64.b64decode(m["image"]["encodedImage"]))
            print("✅ Đã lưu angle_0.png từ base64! Size:", os.path.getsize(target_path))
        else:
            print("⚠️ Không tìm thấy URL hay base64 trong media:", m)
            
        meta = {
            "character_key": "nguyet-dao",
            "project_id": PROJECT_ID,
            "project_name": "Băng Nguyệt Tiên Tử - Nguyệt Dao",
            "angle_0": {
                "media_id": media_id,
                "file": "angle_0.png",
                "image_url": img_url,
                "status": "COMPLETED"
            }
        }
        with open(os.path.join(OUTPUT_DIR, "character_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print("Đã lưu character_meta.json")

except Exception as e:
    print("Error:", e)
    if hasattr(e, "read"):
        print("Error details:", e.read().decode("utf-8", errors="replace"))
    sys.exit(1)

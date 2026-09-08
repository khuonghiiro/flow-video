import urllib.request, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "b1b4897d-a85d-4d97-9736-5ba6b3bf7552"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\vo-tam-tien-nhan"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PROMPT_0 = (
    "2D Xianxia anime chibi character sprite — TRUE DIRECT 0-DEGREE FRONT VIEW.\n"
    "Full body standing centered, facing directly at camera (12 o'clock).\n"
    "CRITICAL — BLANK FACELESS HEAD: Completely BLANK, SMOOTH, FEATURELESS face surface (NO eyes, NO eyebrows, NO nose, NO mouth). Pure smooth porcelain skin with cold ethereal white jade glow.\n"
    "CHARACTER: Vô Tâm Tiên Nhân (Lý Thanh Vũ), male immortal cultivator, 26-27 years old appearance, tall lean athletic physique (185cm, 72kg), dignified cold noble posture.\n"
    "HAIRSTYLE: Long silky jet black hair with faint moonlight frost sheen, tied back into a high ponytail with a vibrant crimson red silk ribbon and an azure quartz hairpin.\n"
    "COSTUME DETAILS:\n"
    "- Deep night-sky blue silk daoist robe (#0D47A1) bordered with silver embroidered ancient runes.\n"
    "- Traditional mandarin collar inlaid with subtle azure sapphire beads.\n"
    "- A vertical golden embroidered line ('Luân Vô Tâm') running down the center front from collar to navel.\n"
    "- Ankle-length dark blue outer coat with white plum blossom embroidery and silver crane feather cuffs.\n"
    "- Pale azure silk trousers with gentle lavender lilac gradient towards ankles.\n"
    "- Golden thousand-year silk sash belt with central azure sapphire bead ('Thanh Lâm Thiên Châu') and twin hanging golden kirin tassel cords.\n"
    "- SHOES: Flat cloud-woven azure cloth boots with soft glowing cyan energy soles (CRITICAL: STRICTLY FLAT, ZERO HEELS, NO HIGH HEELS).\n"
    "WEAPON: Azure frost sword ('Thanh Lâm Kiếm') strapped diagonally across back, scabbard visible behind shoulder.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, bold clean linework, flat cel-shaded coloring.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible from head to feet."
)

print("🚀 Bắt đầu sinh ảnh 0° (Master Root) cho Vô Tâm Tiên Nhân...")
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
        print("Response received!")
        # Find media
        media_list = res_data.get("media", [])
        if not media_list:
            print("Raw response:", json.dumps(res_data, indent=2))
            sys.exit(1)
            
        m = media_list[0]
        media_id = m.get("name")
        print("✅ Media ID:", media_id)
        
        # Check image URL or fifeUrl
        img_url = m.get("fifeUrl") or m.get("servingUri")
        if not img_url and "image" in m:
            img_url = m["image"].get("fifeUrl") or m["image"].get("servingUri")
            
        print("Image URL:", img_url)
        
        # Save image file
        target_path = os.path.join(OUTPUT_DIR, "angle_0.png")
        if img_url:
            print("Tải ảnh về", target_path)
            urllib.request.urlretrieve(img_url, target_path)
            print("✅ Đã lưu angle_0.png thành công! Size:", os.path.getsize(target_path))
        elif "image" in m and "encodedImage" in m["image"]:
            import base64
            with open(target_path, "wb") as f:
                f.write(base64.b64decode(m["image"]["encodedImage"]))
            print("✅ Đã lưu angle_0.png từ base64! Size:", os.path.getsize(target_path))
        else:
            print("⚠️ Không tìm thấy URL hay base64 trong media:", m)
            
        # Write metadata
        meta = {
            "character_key": "vo-tam-tien-nhan",
            "project_id": PROJECT_ID,
            "project_name": "Vô Tâm Tiên Nhân",
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

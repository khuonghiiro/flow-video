import urllib.request, json, sys, os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "29951668-e794-44cb-81e6-dfa24338fc53"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tham-nhuoc-lan"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PROMPT_0 = (
    "MASTER CHARACTER DESIGN — 2D XIANXIA CHIBI — 0° DIRECT FRONT VIEW.\n"
    "CAMERA & POSE: Full body standing centered, facing 100% directly forward at camera (0° strict front view, 12 o'clock). "
    "Symmetrical standing pose, torso upright, shoulders level, arms relaxed at sides, empty hands, legs straight.\n"
    "CRITICAL — BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Completely BLANK, SMOOTH, FEATURELESS face surface "
    "(NO eyes, NO eyebrows, NO nose, NO mouth). The facial skin color MUST seamlessly and uniformly match the neck, ears, and hands "
    "with a fair natural warm peach skin tone. STRICTLY ZERO shiny white porcelain mask, ZERO chalky white enamel face contrast, "
    "ZERO face-neck tone discrepancy. Pure continuous natural flesh tone across head and neck.\n"
    "CRITICAL — ZERO WEAPONS OR PROPS: The character carries NO weapons, NO swords on back or waist, NO musical instruments, "
    "NO props. Both hands are empty and resting naturally.\n"
    "CHARACTER: Thẩm Nhược Lan (Shen Ruolan) — Lan Đình Tiên Cơ, young female immortal maiden (18-19 years old appearance), "
    "slender graceful physique (165cm, 45kg), pure delicate tranquil orchid fairy presence.\n"
    "HAIRSTYLE: Silky long flowing raven-black hair styled with twin delicate butterfly-loop side buns and cascading hair down shoulders, "
    "adorned with delicate carved white jade orchid hairpins and twin flowing pale celadon green silk ribbons.\n"
    "COSTUME DETAILS:\n"
    "- Elegant pale celadon seafoam-jade silk outer robe with flowing wide sleeves over a pure snow-white inner robe.\n"
    "- Delicate silver frost orchid embroidery along the robe lapels and sleeves.\n"
    "- Soft jade-green silk waist sash tied into an elegant butterfly ribbon bow with a round carved celadon orchid jade pendant.\n"
    "- Flowing tiered pleated white silk skirt.\n"
    "- SHOES: Soft white cloth shoes embroidered with tiny orchid blossoms and flat soles (CRITICAL: STRICTLY FLAT, ZERO HEELS, NO HIGH HEELS).\n"
    "LIGHTING & COLOR PALETTE: Harmonious natural pastel palette (pale celadon green, pure snow white, soft silver, warm peach skin), "
    "clean flat cel-shaded anime coloring, bold clean linework. "
    "STRICTLY ZERO neon lighting, ZERO harsh glowing rim lights, ZERO glowing neon edge reflections.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible from head to feet."
)

print("🚀 Bắt đầu sinh ảnh 0° (Master Root) cho Thẩm Nhược Lan...")
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
            "character_key": "tham-nhuoc-lan",
            "project_id": PROJECT_ID,
            "project_name": "Lan Đình Tiên Cơ - Thẩm Nhược Lan",
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

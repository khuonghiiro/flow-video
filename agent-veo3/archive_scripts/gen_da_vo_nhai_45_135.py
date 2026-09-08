import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "7de76f25-e719-452f-8a03-fb6eece897e4"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\da-vo-nhai"

mid_0 = "62a88991-c3d8-4fb5-8cf0-23da064aba43"
mid_90 = "0bdb8722-0411-4fde-baa9-a9dc112f9406"
mid_180 = "ea74ae36-f227-4d77-9732-9579467b7801"

PROMPT_45 = (
    "2D Xianxia anime chibi character sprite — TRUE 45-DEGREE THREE-QUARTER VIEW.\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate exactly halfway between Reference 0° (front view) and Reference 90° (lateral side profile).\n"
    "CRITICAL ROTATED TORSO & SHOULDERS: The character's entire upper body, torso, chest, and hips are ROTATED EXACTLY 45 DEGREES to the left (facing 10:30 o'clock direction). "
    "The chest plane is visibly angled diagonally at 45 degrees toward the left, NOT facing front. "
    "The character's left shoulder is clearly positioned forward in the foreground; "
    "the right shoulder is positioned further back in depth and recessed behind the neck. "
    "The diagonal V-neck collar lapel crosses cleanly from right to left across the angled chest in 3/4 perspective. "
    "Both feet are planted and point diagonally toward the left (10 o'clock direction).\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robes, sleeves, and outer coat hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING HEMS, NO COAT TAILS FLYING BACKWARD. Calm static fabric drape.\n"
    "HAIRSTYLE & IDENTITY: Keep 100% identical hairstyle from references: high topknot with sleek golden coronet and hairpin, "
    "two slender soft side hair strands, and long straight silky black hair flowing down the back.\n"
    "SKIN TONE: Smooth pale fair ivory-white skin tone matching references 100% seamlessly on face, neck, and hands.\n"
    "COSTUME (IDENTICAL RICH DETAILS): Exact same midnight ink-navy martial coat over crisp white inner robe with diagonal collar, "
    "intricate golden cloud patterns and dragon filigree embroidery along lapels, cuffs, and hem. "
    "Broad black waist belt with dual gold border bands and circular gold-framed white jade medallion. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS. "
    "Loose white trousers, flat black cloth boots with gold stitching and flat white soles.\n"
    "ARMS: Left arm in foreground, right arm recessed, empty bare hands, strictly zero weapons, zero props.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body visible."
)

PROMPT_135 = (
    "2D Xianxia anime chibi character sprite — THREE-QUARTER REAR VIEW (135 DEGREES).\n"
    "MULTI-REFERENCE INTERPOLATION: Interpolate between Reference 0° (front) and Reference 180° (rear). "
    "Character turned away from camera, viewing the back-left side of character (facing 1:30 o'clock direction / body rotated 135 degrees). "
    "The character's back is angled in distinct 3/4 perspective: the left shoulder and left sleeve are in the foreground, "
    "while the right shoulder is recessed deep into the background. "
    "The spine and back-seam are viewed at a diagonal 135-degree angle.\n"
    "HAIRSTYLE & IDENTITY: High topknot with golden coronet/hairpin seen in 3/4 rear angle, "
    "long black hair flowing straight down the diagonal back.\n"
    "SKIN TONE: Smooth pale fair ivory-white skin tone matching references 100% seamlessly on neck and hands.\n"
    "COSTUME & FABRIC (STRICTLY FLAT MATTE, ZERO SHINE): Exact same midnight ink-navy martial coat. "
    "STRICTLY FLAT MATTE FABRIC TEXTURE, ZERO METALLIC SHINE, ZERO SILVERY GLOSS, ZERO SPECULAR REFLECTIONS. "
    "Natural flat cel-shaded cloth, intricate golden cloud embroidery on outer sleeve cuffs and lower hem.\n"
    "CRITICAL WAIST BELT REAR: Broad black belt with dual gold border bands wraps smoothly around the lower back. "
    "STRICTLY CONTINUOUS FLAT BELT BAND AROUND REAR WITH ZERO BOW, ZERO RIBBON KNOT, ZERO DECORATIVE TIES. Completely smooth flat belt at rear.\n"
    "NATURAL FABRIC DRAPE UNDER GRAVITY: Robe, coat tails, and sleeves hang straight down naturally along the body under calm gravity. "
    "STRICTLY NO WIND BLOWING, NO BILLOWING FABRIC, NO FLAPPING COAT TAILS, NO HEMS FLYING. Calm static fabric drape.\n"
    "Loose white trousers, and flat black cloth boots pointing away at 135 degrees.\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, strictly zero neon glow.\n"
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
    for attempt in range(3):
        print(f"Generating {name} (attempt {attempt+1})...", flush=True)
        try:
            async with session.post(url, json=body, timeout=120) as resp:
                data = await resp.json()
                media_list = data.get("media", [])
                if not media_list:
                    print(f"Fail {name}: {data}", flush=True)
                    await asyncio.sleep(4)
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
                    print(f"Done {name}! Media ID: {mid}, Size: {os.path.getsize(target_file)}", flush=True)
                    return name, mid, target_file
                elif "image" in m and "encodedImage" in m["image"]:
                    import base64
                    with open(target_file, "wb") as f:
                        f.write(base64.b64decode(m["image"]["encodedImage"]))
                    print(f"Done {name} (b64)! Media ID: {mid}, Size: {os.path.getsize(target_file)}", flush=True)
                    return name, mid, target_file
        except Exception as e:
            print(f"Error {name}: {e}", flush=True)
            await asyncio.sleep(4)
    return name, None, None

async def main():
    print("Generating 45° (ref: [0°, 90°]) and 135° (ref: [0°, 180°]) for Da Vo Nhai...", flush=True)
    results = []
    async with aiohttp.ClientSession() as session:
        # 45° candidates (ref: 0° + 90°)
        c_45_1 = await generate_cand(session, "angle_45_dual_1", PROMPT_45, [mid_0, mid_90])
        await asyncio.sleep(3)
        c_45_2 = await generate_cand(session, "angle_45_dual_2", PROMPT_45, [mid_0, mid_90])
        await asyncio.sleep(3)
        
        # 135° candidates (ref: 0° + 180°)
        c_135_1 = await generate_cand(session, "angle_135_dual_1", PROMPT_135, [mid_0, mid_180])
        await asyncio.sleep(3)
        c_135_2 = await generate_cand(session, "angle_135_dual_2", PROMPT_135, [mid_0, mid_180])
        
        results = [c_45_1, c_45_2, c_135_1, c_135_2]
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "stage_45_135_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed 45° and 135° generation:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

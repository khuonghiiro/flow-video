import asyncio
import aiohttp
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "79a7e17f-ebe3-4f0d-8c85-f270e4c03a7d"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\tieu-dat-than"

PROMPT_0 = (
    "2D Xianxia anime chibi character sprite — MASTER CHARACTER DESIGN, FULL FRONTAL VIEW (0 DEGREES).\n"
    "Full-body standing pose facing directly forward towards camera, perfectly symmetrical stance, "
    "arms resting naturally at sides with open empty hands, bare hands, strictly zero weapons, zero swords, zero props.\n"
    "BLANK FACELESS HEAD & NATURAL UNIFORM SKIN: Smooth featureless blank head with NO eyes, NO nose, NO mouth. "
    "The facial skin is a completely uniform, natural fair warm healthy skin tone that matches the neck and hands 100% seamlessly. "
    "STRICTLY ZERO shiny white porcelain mask, zero mask outline, zero skin tone mismatch.\n"
    "HAIRSTYLE: Jet-black hair styled into a neat high topknot bound by a delicate silver jade crown (guan) with soft white silk ribbon tails, "
    "with silky long black hair flowing straight down the back.\n"
    "COSTUME: Deep royal azure silk martial robe over a crisp white inner robe with diagonal collar wrap, "
    "subtle silver cloud embroidery along lapels and sleeve cuffs, dark navy-cyan silk waist sash tied neatly with a circular white jade medallion, "
    "white loose martial trousers, and flat black cloth boots with white soles (flat soles, strictly zero heels).\n"
    "STYLE: Pure flat 2D anime chibi sprite illustration, clean crisp linework, flat cel-shaded coloring, harmonious natural colors, strictly zero neon glow.\n"
    "BACKGROUND: Solid chroma-key green #00FF00. Centered, full body completely visible from head to toe."
)

async def generate_cand(session, name, prompt):
    url = "http://127.0.0.1:8100/api/flow/generate-image"
    body = {
        "prompt": prompt,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
    }
    for attempt in range(3):
        print(f"Generating {name} (attempt {attempt+1})...", flush=True)
        try:
            async with session.post(url, json=body, timeout=120) as resp:
                data = await resp.json()
                media_list = data.get("media", [])
                if not media_list:
                    print(f"Fail {name}: {data}", flush=True)
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
            await asyncio.sleep(3)
    return name, None, None

async def main():
    print("Starting Stage 1 (0° Master Root) for Xiao Yichen...", flush=True)
    async with aiohttp.ClientSession() as session:
        t1 = generate_cand(session, "angle_0_c1", PROMPT_0)
        t2 = generate_cand(session, "angle_0_c2", PROMPT_0)
        results = await asyncio.gather(t1, t2)
        
    res_dict = {name: {"media_id": mid, "file": fpath} for name, mid, fpath in results}
    with open(os.path.join(OUTPUT_DIR, "stage1_results.json"), "w", encoding="utf-8") as f:
        json.dump(res_dict, f, indent=2, ensure_ascii=False)
    print("Completed Stage 1:", res_dict, flush=True)

if __name__ == "__main__":
    asyncio.run(main())

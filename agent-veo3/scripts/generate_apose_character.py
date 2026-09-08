"""Generate A-Pose Image for Diệp Thanh Lam for Modular Part Animation.
"""
import asyncio
import json
import logging
import os
import sys
import urllib.request
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("apose_generator")

PROJECT_ID = "7c7b4d45-2416-4902-b77a-1601a0aecff9"
REF_MEDIA_ID = "973a46d8-4d96-4657-aea8-ec7861080166"
DEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "diep-thanh-lam", "parts_test"))
os.makedirs(DEST_DIR, exist_ok=True)

PROMPT_A_POSE = (
    "Masterpiece 2D Xianxia manhwa anime sprite, mature 4.8 heads chibi ratio, bold clean black line art, "
    "flat cel-shaded coloring. Diệp Thanh Lam (Ye Qinglan), pure ice fairy maiden, long black silky hair "
    "with butterfly double top buns, crystal azure hairpin and silver ornaments. "
    "Pure snow white inner silk robe with crossed collar, pale icy azure gradient outer fairy silk robe "
    "with celestial cloud silver embroidery, pale mint waist sash with green lotus flower buckle. "
    "RIGGING A-POSE: Standing facing forward directly at camera, full body from head to flat lotus shoes, "
    "both arms held outward 40 degrees away from the torso in a clean symmetrical A-pose, "
    "wide hanging silk sleeves draping freely with CLEAR VISIBLE GREEN GAP between arms and torso ribs, "
    "unobstructed waist and ribs, no occlusion. "
    "Solid pure green chroma key background #00FF00, sharp crisp silhouette, sprite sheet ready."
)

async def main():
    logger.info("Sending generate-image request for A-Pose...")
    payload = {
        "prompt": PROMPT_A_POSE,
        "project_id": PROJECT_ID,
        "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_ONE",
        "character_media_ids": [REF_MEDIA_ID]
    }
    
    url = "http://127.0.0.1:8100/api/flow/generate-image"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=90) as resp:
            data = await resp.json()
            
        logger.info("Response received: %s", str(data)[:200])
        
        # Extract media
        media_id = None
        img_url = None
        
        media_list = data.get("media", [])
        if not media_list and "data" in data:
            media_list = data["data"].get("media", [])
            
        if media_list:
            m = media_list[0]
            media_id = m.get("name")
            img_block = m.get("image", {})
            gen_img = img_block.get("generatedImage", {}) if isinstance(img_block.get("generatedImage"), dict) else {}
            img_url = gen_img.get("fifeUrl") or img_block.get("fifeUrl") or m.get("fifeUrl")
            
        if not media_id or not img_url:
            logger.error("Failed to extract media_id or img_url: %s", data)
            return False
            
        logger.info("Generated A-Pose image! media_id=%s", media_id)
        logger.info("Downloading image from CDN: %s...", img_url[:80])
        
        dest_path = os.path.join(DEST_DIR, "apose_0.png")
        async with session.get(img_url, timeout=60) as img_resp:
            content = await img_resp.read()
            with open(dest_path, "wb") as f:
                f.write(content)
                
        logger.info("Saved A-Pose image to: %s (Size: %d bytes)", dest_path, len(content))
        
        # Save metadata info
        meta_info = {
            "media_id": media_id,
            "url": img_url,
            "file": "parts_test/apose_0.png",
            "prompt": PROMPT_A_POSE,
            "size_bytes": len(content)
        }
        with open(os.path.join(DEST_DIR, "apose_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta_info, f, indent=2, ensure_ascii=False)
            
        return True

if __name__ == "__main__":
    asyncio.run(main())

"""Test generating video animation for isolated arm part.
"""
import asyncio
import json
import logging
import os
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_part_video")

PROJECT_ID = "7c7b4d45-2416-4902-b77a-1601a0aecff9"
ARM_MEDIA_ID = "683b991f-27dc-409b-8a9b-bd2773087b7f"
DEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "diep-thanh-lam", "parts_test"))
os.makedirs(DEST_DIR, exist_ok=True)

PROMPT = (
    "2D cel-shaded animation of an isolated fairy silk robe arm and sleeve, gentle waving and fluttering motion in ethereal wind, "
    "delicate hand gesture, pure solid green chroma key background #00FF00, static camera, seamless 4-second loop, anime Xianxia sprite"
)

async def main():
    logger.info("Submitting video generation request for isolated arm...")
    url_gen = "http://127.0.0.1:8100/api/flow/generate-video"
    payload = {
        "start_image_media_id": ARM_MEDIA_ID,
        "end_image_media_id": ARM_MEDIA_ID,
        "prompt": PROMPT,
        "project_id": PROJECT_ID,
        "scene_id": "test_arm_loop_0",
        "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "duration": 4.0,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url_gen, json=payload, timeout=60) as resp:
            data = await resp.json()
            
        logger.info("Generation submitted! Response: %s", str(data)[:200])
        workflows = data.get("workflows", [])
        operations = data.get("operations", [])
        
        if not workflows and not operations:
            logger.error("No workflows or operations returned: %s", data)
            return
            
        logger.info("Polling for video completion...")
        url_check = "http://127.0.0.1:8100/api/flow/check-status"
        vid_media_id = None
        signed_url = None
        
        if workflows:
            check_payload = {"workflows": workflows, "project_id": PROJECT_ID}
            for poll in range(50):
                await asyncio.sleep(6)
                try:
                    async with session.post(url_check, json=check_payload, timeout=30) as c_resp:
                        sdata = await c_resp.json()
                except Exception as e:
                    logger.warning("Poll error: %s", e)
                    continue
                    
                for wf in sdata.get("workflows", []):
                    st = wf.get("status", "")
                    if st in ("MEDIA_GENERATION_STATUS_SUCCESSFUL", "SUCCESSFUL") or wf.get("done"):
                        vid_media_id = wf.get("primary_media_id") or wf.get("media", {}).get("media_id")
                        signed_url = wf.get("media", {}).get("url")
                        break
                    if st in ("MEDIA_GENERATION_STATUS_FAILED", "FAILED"):
                        logger.error("Generation failed: %s", wf)
                        return
                if vid_media_id:
                    break
        else:
            check_payload = {"operations": operations}
            for poll in range(50):
                await asyncio.sleep(6)
                try:
                    async with session.post(url_check, json=check_payload, timeout=30) as c_resp:
                        sdata = await c_resp.json()
                except Exception as e:
                    logger.warning("Poll error: %s", e)
                    continue
                    
                for op in sdata.get("operations", []):
                    st = op.get("status", "")
                    if st in ("MEDIA_GENERATION_STATUS_SUCCESSFUL", "SUCCESSFUL"):
                        meta_vid = op.get("operation", {}).get("metadata", {}).get("video", {})
                        vid_media_id = meta_vid.get("mediaId")
                        signed_url = meta_vid.get("fifeUrl") or meta_vid.get("servingUri")
                        break
                    if st in ("MEDIA_GENERATION_STATUS_FAILED", "FAILED"):
                        logger.error("Generation failed: %s", op)
                        return
                if vid_media_id:
                    break
                    
        if not vid_media_id:
            logger.error("Polling timed out!")
            return
            
        logger.info("Video generation SUCCESSFUL! Media ID: %s", vid_media_id)
        
        # Download MP4
        if not signed_url:
            url_redirect = f"http://127.0.0.1:8100/api/flow/media-redirect-url/{vid_media_id}"
            for _ in range(10):
                try:
                    async with session.get(url_redirect, timeout=15) as r:
                        res_data = await r.json()
                        if res_data.get("status") == 200:
                            u = res_data.get("data", {}).get("url", "")
                            if u and "flow-content.google" in u:
                                signed_url = u
                                break
                except Exception:
                    pass
                await asyncio.sleep(2)
                
        if not signed_url:
            logger.error("Could not obtain signed URL")
            return
            
        dest_file = os.path.join(DEST_DIR, "isolated_arm_4s.mp4")
        logger.info("Downloading video from CDN...")
        async with session.get(signed_url, timeout=90) as r:
            raw_bytes = await r.read()
            
        with open(dest_file, "wb") as f:
            f.write(raw_bytes)
            
        logger.info("Saved isolated arm video to: %s (Size: %d bytes)", dest_file, len(raw_bytes))

if __name__ == "__main__":
    asyncio.run(main())

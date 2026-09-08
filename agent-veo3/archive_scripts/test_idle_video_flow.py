import asyncio
import aiohttp
import json
import os
import sys
import uuid

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ID = "7de76f25-e719-452f-8a03-fb6eece897e4"
OUTPUT_DIR = r"e:\UngDung_PC\Flow-App\AI-Render-Video\agent-veo3\output\da-vo-nhai\videos\dung-yen"
os.makedirs(OUTPUT_DIR, exist_ok=True)

mid_0 = "62a88991-c3d8-4fb5-8cf0-23da064aba43"

PROMPT_IDLE_0 = (
    "4-second seamless loop IDLE STANDING (0° direct front view). "
    "Character stands completely still and motionless facing camera. "
    "STRICT ARM & HAND IMMOBILITY LOCK: Both arms hang completely relaxed straight down along sides and DO NOT MOVE. "
    "Hands and fingers remain completely still and motionless at sides. "
    "STRICTLY FORBIDDEN TO MOVE ARMS, STRICTLY ZERO ARM RAISING, ZERO HAND MOVEMENT, ZERO TOUCHING CHEST, ZERO RAISING PALMS. "
    "ONLY FABRIC, SLEEVES, HAIR & ACCESSORY WIND DYNAMICS: The only visible movement is a gentle ambient breeze softly blowing through the clothing: "
    "gentle fluttering of the wide robe sleeves, outer coat hem borders, and silky long black hair falling behind swaying softly in the breeze. "
    "Any hair ornaments or fixed belt accessories sway subtly and naturally with the cloth. "
    "Body, torso, head, and feet remain completely static and anchored to the floor plane. "
    "Faceless blank mannequin head remains completely smooth with uniform skin tone seamlessly matching neck. "
    "STRICTLY ZERO hopping, ZERO bouncing, ZERO body turning. STRICTLY ZERO weapons or props. "
    "Static camera, seamless loop: first frame = last frame. Solid green #00FF00 background."
)

async def main():
    print("Submitting 4s loop video with STRICT ARM IMMOBILITY LOCK...", flush=True)
    url_gen = "http://127.0.0.1:8100/api/flow/generate-video"
    url_check = "http://127.0.0.1:8100/api/flow/check-status"

    body = {
        "start_image_media_id": mid_0,
        "end_image_media_id": mid_0,
        "prompt": PROMPT_IDLE_0,
        "project_id": PROJECT_ID,
        "scene_id": f"scene_{uuid.uuid4().hex[:8]}",
        "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "user_paygate_tier": "PAYGATE_TIER_TWO",
        "duration": 4.0
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url_gen, json=body, timeout=60) as resp:
            data = await resp.json()
            print("Submission response:", json.dumps(data, indent=2, ensure_ascii=False), flush=True)

        operations = []
        for op in data.get("operations", []):
            name = op.get("name")
            if name:
                operations.append({"name": name, "projectId": PROJECT_ID})

        for m in data.get("media", []):
            name = m.get("name")
            if name:
                operations.append({"name": name, "projectId": PROJECT_ID})

        if not operations:
            print("No operations or media returned!", flush=True)
            return

        print(f"Tracking operations: {operations}", flush=True)

        max_polls = 40
        for i in range(max_polls):
            await asyncio.sleep(8)
            try:
                async with session.post(url_check, json={"operations": operations}, timeout=30) as check_resp:
                    sdata = await check_resp.json()

                for m in sdata.get("media", []):
                    mst = m.get("mediaMetadata", {}).get("mediaStatus", {}).get("mediaGenerationStatus", "")
                    blob_size = m.get("mediaMetadata", {}).get("mediaBlobSize", "")
                    print(f"Poll {i+1}/{max_polls} -> Media Status: {mst} (Blob: {blob_size} bytes)", flush=True)
                    if mst in ("MEDIA_GENERATION_STATUS_SUCCESSFUL", "SUCCESSFUL"):
                        print(f"\n SUCCESS! 4s Loop Video generated successfully on Google Flow!")
                        print(f"Media Name: {m.get('name')}")
                        print(f"Project ID: {PROJECT_ID}")
                        print(f"Flow Web URL: https://labs.google/fx/tools/flow/project/{PROJECT_ID}")
                        return

                    if mst in ("MEDIA_GENERATION_STATUS_FAILED", "FAILED"):
                        print(f"FAILED: {m}", flush=True)
                        return

            except Exception as e:
                print(f"Poll error: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())

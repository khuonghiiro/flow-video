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
    "4-second seamless loop IDLE STANDING (0° front view). "
    "Character stands calmly still facing camera. "
    "Soft gentle ambient mountain breeze subtly flutters wide robe sleeves, outer coat hems, and long black hair falling behind naturally. "
    "Organic subtle chest breathing rhythm. Arms rest relaxed at sides with minimal subtle resting finger micro-adjustments. "
    "Hair realistically rooted to scalp with natural fluid secondary motion, ZERO rigid wig bounce. "
    "CRITICAL MOTION STABILITY CONSTRAINTS (STRICT ANTI-GLITCH LOCK): "
    "Movement is natural, authentic, and dignified. "
    "The jade medallion at center waist is a fixed solid buckle; STRICTLY ZERO swinging pendants, ZERO dangling tassels, ZERO fake hair ribbons. "
    "Hands and forearms strictly stay below chest level at all times. "
    "Feet remain firmly grounded in place, STRICTLY ZERO hopping, ZERO bouncing, ZERO floating. "
    "Torso, shoulders, and head remain rock-steady and level. "
    "Faceless blank mannequin head remains completely smooth with natural skin color seamlessly matching neck. "
    "STRICTLY ZERO weapons, swords, or props. STRICTLY ZERO neon glow. "
    "Seamless loop: first frame = last frame. Camera static. Solid green #00FF00 background."
)

async def main():
    print(f"Submitting 4s loop video generation for Da Vo Nhai (0° Idle)...", flush=True)
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
        print("Sending generate-video request...", flush=True)
        async with session.post(url_gen, json=body, timeout=60) as resp:
            data = await resp.json()
            print("Response:", json.dumps(data, indent=2, ensure_ascii=False), flush=True)

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
            print("No operations returned!", flush=True)
            return

        print(f"Tracking operations: {operations}", flush=True)

        # Polling loop
        max_polls = 60
        for i in range(max_polls):
            await asyncio.sleep(10)
            print(f"Polling status ({i+1}/{max_polls})...", flush=True)
            try:
                async with session.post(url_check, json={"operations": operations}, timeout=30) as check_resp:
                    sdata = await check_resp.json()

                # Check operations list
                done = False
                video_url = None
                for op in sdata.get("operations", []):
                    st = op.get("status", "")
                    print(f"Op Status: {st}", flush=True)
                    if st in ("MEDIA_GENERATION_STATUS_SUCCESSFUL", "SUCCESSFUL"):
                        vid = op.get("operation", {}).get("metadata", {}).get("video", {})
                        video_url = vid.get("fifeUrl") or vid.get("servingUri") or vid.get("url")
                        done = True
                        break
                    elif st in ("MEDIA_GENERATION_STATUS_FAILED", "FAILED"):
                        print("Generation failed:", op)
                        return

                for m in sdata.get("media", []):
                    mst = m.get("mediaMetadata", {}).get("mediaStatus", {}).get("mediaGenerationStatus", "")
                    print(f"Media Status: {mst}", flush=True)
                    if mst in ("MEDIA_GENERATION_STATUS_SUCCESSFUL", "SUCCESSFUL"):
                        vid = m.get("video", {})
                        video_url = vid.get("fifeUrl") or vid.get("servingUri") or vid.get("url")
                        done = True
                        break

                if done and video_url:
                    print(f"Video ready! URL: {video_url}", flush=True)
                    target_mp4 = os.path.join(OUTPUT_DIR, "angle_0.mp4")
                    async with session.get(video_url) as v_resp:
                        v_content = await v_resp.read()
                        with open(target_mp4, "wb") as f:
                            f.write(v_content)
                    print(f"Saved video to {target_mp4} (Size: {os.path.getsize(target_mp4)} bytes)", flush=True)
                    return

            except Exception as e:
                print(f"Polling error: {e}", flush=True)

    print("Timed out waiting for video generation.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())

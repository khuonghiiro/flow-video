# /fk-gen-loop-4s — Generate 4s Seamless Loop Video (Identical Start & End Frames)

Skill to generate seamless 4-second looping character animations (idle breathing, hovering, combat stance) for 2D sprites, VFX, and avatars.

> *User Reference (Tiếng Việt)*: See [../skills_vi/fk-gen-loop-4s.md](../skills_vi/fk-gen-loop-4s.md) for the Vietnamese documentation.

**Usage:** `/fk-gen-loop-4s <project_id> <video_id> [scene_id]`

---

## 🎯 Mechanism (Start-End Frame Matching)

To create a closed-loop animation:
1. Select or generate a base static frame (`start_frame`).
2. **Assign that exact frame as the end frame** (`end_scene_media_id = image_media_id`).
3. Veo3 dispatches via `start_end_frame_2_video` (RPC `nprQif`) with a 4s duration, constraining frame 0s and frame 4s to match identically, producing an infinite loop.

---

## 📋 Step-by-Step Procedure

### Step 0: Check Orientation & Fetch Project Meta
```bash
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
ORI=$(cat ${OUTDIR}/meta.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('orientation','HORIZONTAL'))")
ori=$(echo "$ORI" | tr '[:upper:]' '[:lower:]')
```

### Step 1: Verify Scene Image
Fetch scenes for the video:
```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```
- If scene has no image yet (`${ori}_image_status != "COMPLETED"`): run `/fk-gen-images <PID> <VID>` first.
- Confirm `${ori}_image_media_id` is a valid 36-char UUID.

### Step 2: Set Start Frame = End Frame
For every scene requiring a loop, assign `${ori}_end_scene_media_id` to `${ori}_image_media_id`:
```bash
IMG_ID=$(curl -s "http://127.0.0.1:8100/api/scenes/<SID>" | python3 -c "import sys,json; print(json.load(sys.stdin)['${ori}_image_media_id'])")

curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d "{\"${ori}_end_scene_media_id\": \"${IMG_ID}\"}"
```

### Step 3: Set Transition Prompt for 4s Loop
```bash
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{
    "transition_prompt": "4-second seamless looping animation, starting and ending at the exact same pose. Smooth natural idle breathing, gentle hair and fabric flutter, fluid subtle movement that loops back seamlessly to frame 0. Fixed centered camera, no background shift, pure chroma green background #00FF00 preserved with zero artifacts."
  }'
```

### Step 4: Submit Batch Video Generation Request
```bash
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"type": "GENERATE_VIDEO", "scene_id": "<SID>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"}
    ]
  }'
```

The server automatically invokes `start_end_frame_2_video` (RPC `nprQif`) because `end_scene_media_id` is populated.

### Step 5: Poll Status
```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO"
```
When `done: true`, the seamless 4s loop is ready.

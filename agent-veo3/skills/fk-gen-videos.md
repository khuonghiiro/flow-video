Generate videos for all scenes using Veo3.1 batch API with T2V, I2V, and F2F support.

> **Overrides** `flowkit/skills/fk-gen-videos.md` with Veo3.1 wire protocol support (T2V, F2F chaining, count x1-x4).

Usage: `/fk-gen-videos <project_id> <video_id>`

## Step 0: Detect orientation

```bash
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
ORI=$(cat ${OUTDIR}/meta.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('orientation','HORIZONTAL'))")
ori=$(echo "$ORI" | tr '[:upper:]' '[:lower:]')
```
**NEVER hardcode VERTICAL or HORIZONTAL.** Use `${ORI}` for API params, `${ori}_*` for DB field lookups.

## Step 1: Pre-check — all scene images must be ready

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

**ABORT** if any scene is missing `${ori}_image_media_id` (UUID) or `${ori}_image_status` != `"COMPLETED"`. Tell user to run `/fk-gen-images` first.

## Step 2: Filter scenes needing video

Only scenes where `${ori}_video_status` != `"COMPLETED"` or `${ori}_video_media_id` is missing.

## Step 3: Submit ALL requests at once

The server handles throttling automatically (max 5 concurrent, 10s cooldown). Submit everything in one batch call. Video generation takes 2-5 minutes per scene.

```bash
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"type": "GENERATE_VIDEO", "scene_id": "<SID1>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"},
      {"type": "GENERATE_VIDEO", "scene_id": "<SID2>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"}
    ]
  }'
```

Build the `requests` array from ALL scenes filtered in Step 2. Do NOT manually batch or loop.

Poll aggregate status every 30s until done (videos take longer):

```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO"
# Wait for: "done": true
# If "all_succeeded": false → some failed, check individual failures
```

## Step 4: Verify

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

## Step 5: Output

Print results table:
| Scene | Order | video_status | video_media_id | video_url |
|-------|-------|-------------|---------------|-----------|

Print: "All videos ready. Run /fk-concat <VID> to download and merge."

## Veo3.1 Direct API (Alternative — /flow/generate-video)

For **manual/direct** video generation outside the batch worker, use these endpoints:

### T2V (Text-to-Video) — 0 images, prompt only
```bash
curl -X POST http://127.0.0.1:8100/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A sunset over the ocean, cinematic 4K",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "duration_s": 8,
    "model_family": "veo",
    "count": 2
  }'
```
- RPC: `YhhmEf` | Duration: 4s, 6s, 8s | Count: 1-4

### I2V (Image-to-Video) — 1 start image
```bash
curl -X POST http://127.0.0.1:8100/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<MEDIA_ID>",
    "prompt": "Character walks forward",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "duration_s": 8,
    "model_family": "veo",
    "count": 1
  }'
```
- RPC: `eb1hJf` | Duration: 8s | Count: 1

### F2F (Frame-to-Frame) — start + end images
```bash
curl -X POST http://127.0.0.1:8100/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<START_MEDIA_ID>",
    "end_image_media_id": "<END_MEDIA_ID>",
    "prompt": "Character transitions from sitting to standing",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "duration_s": 6,
    "model_family": "veo",
    "count": 2
  }'
```
- RPC: `nprQif` | Duration: 4s, 6s, 8s | Count: 1-4

### R2V (Reference-to-Video) — 1-3 reference images
```bash
curl -X POST http://127.0.0.1:8100/flow/generate-video-refs \
  -H "Content-Type: application/json" \
  -d '{
    "reference_media_ids": ["<REF_ID_1>", "<REF_ID_2>"],
    "prompt": "A character walking through a garden",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "count": 2
  }'
```
- RPC: `MZZa6b` | Duration: 8s only | Max 3 refs | Count: 1-4

## Important rules

- **GENERATE vs REGENERATE:** `GENERATE_VIDEO` skips scenes already `COMPLETED`. To force-regenerate, reset `${ori}_video_status` to `PENDING` first, then submit.
- **Cascade on regen:** Regenerating a video auto-clears the upscale status for that scene.
- **Count parameter:** `count` (1-4) creates multiple videos from the same prompt in parallel. Useful for selecting the best result.
- **Chain video prompt rule (CRITICAL):** Chain scenes with children use `transition_prompt` for video generation, NOT `video_prompt`.
- **Chain cascade (CRITICAL):** When regenerating a scene that has CONTINUATION children, you MUST also regenerate images + videos for all descendants in the chain.

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

### T2V (Text-to-Video) — 0 ảnh, chỉ prompt
```bash
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
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
- RPC: `YhhmEf` | Model: `veo_3_1_t2v_lite_low_priority` | Duration: 4s, 6s, 8s | Count: 1-4

### I2V / R2V (Tạo video với ảnh) — 1 đến 3 ảnh tham chiếu
> 💡 Google Flow chuẩn: Không có cơ chế frame đơn lẻ trong F2F. Mọi yêu cầu tạo video từ 1-3 ảnh đều dùng RPC `MZZa6b`.
```bash
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<MEDIA_ID>",
    "prompt": "Cinematic slow camera glide forward, glowing particles",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "duration_s": 8,
    "model_family": "veo",
    "count": 2
  }'
```
- RPC: `MZZa6b` | Model: `veo_3_1_r2v_lite_low_priority` | Duration: **8s cố định** (chế độ tạo video với ảnh chỉ hỗ trợ 8s) | Tối đa 3 ảnh tham chiếu | Count: 1-4

### F2F (Tạo video từ Frame to Frame) — BẮT BUỘC ĐỦ 2 FRAME (Start + End)
> ⚠️ Cảnh báo: F2F bắt buộc phải có đồng thời cả Start Frame và End Frame. Nếu chỉ truyền 1 frame, hệ thống tự động điều hướng sang R2V `MZZa6b`.
```bash
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<START_MEDIA_ID>",
    "end_image_media_id": "<END_MEDIA_ID>",
    "prompt": "Character transitions smoothly from sitting to standing",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "duration_s": 8,
    "model_family": "veo",
    "count": 2
  }'
```
- RPC: `nprQif` | Model: `veo_3_1_interpolation_lite_low_priority` | Duration: 4s, 6s, 8s (mặc định 8s) | Count: 1-4

### R2V trực tiếp (Reference-to-Video) — 1 đến 3 ảnh tham chiếu
```bash
curl -X POST http://127.0.0.1:8100/api/flow/generate-video-refs \
  -H "Content-Type: application/json" \
  -d '{
    "reference_media_ids": ["<REF_ID_1>", "<REF_ID_2>"],
    "prompt": "A character walking through a glowing garden",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "count": 2
  }'
```
- RPC: `MZZa6b` | Model: `veo_3_1_r2v_lite_low_priority` | Duration: 8s cố định | Max 3 refs | Count: 1-4

## Important rules

- **GENERATE vs REGENERATE:** `GENERATE_VIDEO` skips scenes already `COMPLETED`. To force-regenerate, reset `${ori}_video_status` to `PENDING` first, then submit.
- **Cascade on regen:** Regenerating a video auto-clears the upscale status for that scene.
- **Count parameter:** `count` (1-4) creates multiple videos from the same prompt in parallel. Useful for selecting the best result.
- **Chain video prompt rule (CRITICAL):** Chain scenes with children use `transition_prompt` for video generation, NOT `video_prompt`.
- **Chain cascade (CRITICAL):** When regenerating a scene that has CONTINUATION children, you MUST also regenerate images + videos for all descendants in the chain.

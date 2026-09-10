Generate videos with automatic scene chaining via Frame-to-Frame (nprQif).

> **Overrides** `flowkit/skills/fk-gen-chain-videos.md` — F2F chaining is NOW SUPPORTED on the batch API via `nprQif` RPC.

Usage: `/fk-gen-chain-videos <project_id> <video_id>`

## F2F Chaining is NOW AVAILABLE

~~Flow's payload has an aspect slot and a single source-image slot; the end-image slot was never captured~~

**FIXED:** The `nprQif` RPC endpoint has been captured and implemented. Frame-to-Frame video generation (start + end image) now works via `build_interpolation_request()` in `extension_patcher.py`.

- **RPC:** `nprQif`
- **Duration:** 8s (`veo_3_1_interpolation_lite_low_priority` or ultra variant). Veo 3.1 interpolation wire model natively generates 8s video.
- **Count:** x1-x4 parallel generations
- **Requires:** Both `start_image_media_id` AND `end_image_media_id`

## How chaining works

For any scene that has a CHILD in the chain (i.e. some other scene with `parent_scene_id == this.id`):

```
Scene N (chain head or middle): startImage = sceneN.image, endImage = sceneN+1.image
                                → video plays FROM sceneN.image TO sceneN+1.image

Scene N+1 (next in chain):      startImage = sceneN+1.image, endImage = sceneN+2.image (if N+2 exists)

Last scene in chain (no child): startImage = lastScene.image, NO endImage
                                → plain R2V/I2V (MZZa6b - Tạo video với ảnh), no chained transition
```

**Key invariant**: at the cut between two consecutive chain scenes, `sceneN.video.last_frame == sceneN+1.image == sceneN+1.video.first_frame` → **concat is seamless**.

## Step 1: Pre-check

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

ABORT if any scene is missing `${ori}_image_media_id` (UUID).

## Step 2: Set up end_scene_media_ids for chaining

For each scene that has a CHILD in the chain, set its `${ori}_end_scene_media_id` to that **child** scene's `${ori}_image_media_id`:

```bash
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{"${ori}_end_scene_media_id": "<child_scene_image_media_id>"}'
```

Logic:
1. Sort scenes by `display_order`
2. Build a child map: `parent_id -> child_scene`
3. For each scene `S`:
   - If `S` has a child → set `${ori}_end_scene_media_id = child.${ori}_image_media_id`
   - Else (no child = chain tail or standalone ROOT) → leave null

## Step 3: Submit ALL video requests at once

The worker reads `${ori}_end_scene_media_id` and passes it as `end_image_media_id` to the API. This triggers the `nprQif` F2F path instead of plain `eb1hJf` I2V.

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

Poll aggregate status every 30s until done:

```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO"
```

## Direct API (Manual F2F)

```bash
curl -X POST http://127.0.0.1:8100/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<START_MEDIA_ID>",
    "end_image_media_id": "<END_MEDIA_ID>",
    "prompt": "Smooth transition between frames",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "duration_s": 6,
    "model_family": "veo",
    "count": 2
  }'
```

## F2F Model Keys by Duration

| Duration | Model Key | Notes |
|---|---|---|
| 4s | `veo_3_1_i2v_s_lite_4s_fl_low_priority` | `_fl_` = first+last |
| 6s | `veo_3_1_i2v_s_lite_6s_fl_low_priority` | Confirmed from logs |
| 8s | `veo_3_1_interpolation_lite_low_priority` | Generic interpolation |

## Known Limitation: Concat Gap

When concatenating chained videos, the endImage frames of scene N overlap with the startImage frames of scene N+1. This produces **10-16 static/duplicate frames (~0.4-0.7s)** at each cut point.

**Mitigations:**
- **Trim overlap** — use `trim_start` / `trim_end` on scenes (0.4-0.7s)
- **Don't overuse chaining** — only chain scenes needing smooth visual continuity
- **Mix techniques** — alternate chained and unchained scenes

## Step 4: Output

Print table:
| Scene | Order | Chain | endImage from | video_status | Duration |
|-------|-------|-------|---------------|-------------|----------|

Print: "Chained videos ready. Run /fk-concat <VID> to merge."

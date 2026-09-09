# CRITICAL RULE: NEVER MODIFY ANY FILE IN flowkit/

## 1. Upstream Core Immutability
- The directory `flowkit/` is strictly upstream core engine code.
- **NEVER** edit, modify, delete, or create files directly within `flowkit/`.
- All enhancements, bug fixes, RPC additions, model mappings, and feature overrides MUST be implemented entirely in `agent-veo3/`.

## 2. Extension & Monkey-Patching Pattern
- `agent-veo3` boots upstream `flowkit` via `flowkit_loader.py` and applies dynamic non-invasive patches via `agent-veo3/agent/extension_patcher.py`.
- Custom endpoints are mounted under `agent-veo3/agent/api/veo3_routes.py`.
- Any behavior changes to `FlowClient`, `flow_batch`, `worker`, or `crud` MUST be patched dynamically at runtime in `extension_patcher.py`.
- `flowkit` acts purely as an intermediary/foundation that `agent-veo3` inherits and overrides.

## 3. Video Mode Terminology & Model Selection
- **IMAGE_TO_VIDEO (i2v / frame_2_video)**:
  - Input: 1 image (`start_image_media_id`) + action prompt.
  - No end frame (`end_image_media_id = None`).
  - Wire RPC: `eb1hJf` (`RPC_GEN_VIDEO`).
  - Model keys: `veo_3_1_i2v_lite_low_priority` (default), `veo_3_1_i2v_lite`, `veo_3_1_i2v_s_fast_ultra`.
- **FRAME_TO_FRAME (interpolation / start_end_frame_2_video)**:
  - Input: 2 images (`start_image_media_id` AND `end_image_media_id`) + transition prompt.
  - Wire RPC: `nprQif` (`RPC_GEN_INTERPOLATION`).
  - Model keys: `veo_3_1_interpolation_lite_low_priority` (default), `veo_3_1_interpolation_lite`, `veo_3_1_interpolation_fast_ultra`.

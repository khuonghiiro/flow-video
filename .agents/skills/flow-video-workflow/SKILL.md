---
name: flow-video-workflow
description: Complete guide and workflow procedures for Google Flow Video and Agent Veo3 pipelines, including API endpoints, batch processing, prompt guidelines, and media orchestration.
---

# Google Flow Video & Agent Veo3 Pipeline Workflow

Use this skill when interacting with, extending, debugging, or executing AI video generation pipelines in the `flow-video` workspace.

## 1. System Architecture & Ports

- **Agent Backend**: `http://127.0.0.1:8100` (FastAPI + SQLite `flow_agent.db`)
- **WebSocket Bridge**: `ws://127.0.0.1:9222` (Agent runs WS server; Chrome Extension connects as client)
- **Dashboard UI**: `http://localhost:5173` (React 19 + Vite in `flowkit/dashboard`)
- **Google Flow API**: Proxied via Chrome MV3 Extension on `flow.google.com` (batchexecute RPCs)

## 2. Pre-flight Verification

Before initiating any media generation task, ALWAYS verify:
```bash
curl -s http://127.0.0.1:8100/health
```
Must return:
```json
{"status": "ok", "version": "...", "extension_connected": true}
```
If `extension_connected` is `false`, the Chrome Extension must be active and open on `flow.google.com`.

## 3. The 10-Step Video Production Pipeline

```
1. Health check      GET  /health → extension_connected: true
2. Create project    POST /api/projects (with name, entities, material style)
3. Create video      POST /api/videos (with project_id, title)
4. Create scenes     POST /api/scenes (with video_id, prompt, video_prompt, character_names)
5. Gen ref images    POST /api/requests/batch → poll /api/requests/batch-status?project_id=<PID>
                     (Wait until all entities have valid UUID media_id)
6. Gen scene images  POST /api/requests/batch → poll /api/requests/batch-status?video_id=<VID>
                     (Wait until all scenes have image_media_id)
7. Gen video clips   POST /api/requests/batch → poll /api/requests/batch-status?video_id=<VID>
                     (Veo2/Veo3 clips take 2-5 min each)
8. (Optional) 4K     POST /api/requests/batch (Tier 2 upscale)
9. (Optional) TTS    Create voice template → POST /api/videos/{vid}/narrate
10. Final Concat     ffmpeg normalize + trim overlap + stitch video clips
```

## 4. Critical Prompt & Media Rules

1. **Media ID Format**:
   - MUST ALWAYS be standard 36-char UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`.
   - Never use base64 `CAMS...` strings.
   - If response URL contains `fifeUrl`, extract UUID from `/image/{UUID}` or `/media/{UUID}`.

2. **Scene Prompts = Action Only**:
   - Only describe camera motion, lighting, environmental physics, and character actions.
   - **NEVER re-describe character visual appearance** in scene prompts. The `imageInputs` reference images guarantee visual identity consistency.

3. **Sub-clip Timing in Video Prompts**:
   - For 4s/6s/8s clips, partition action by timestamps:
     `0-3s: [Subject performs action A while camera pushes in]. 3-6s: [Subject reacts with action B]. 6-8s: [Camera pans to reveal ending environment].`
   - Spoken dialogue inside quotes: `Character says "Hello world."` (max 10-15 words per 2-3s).

4. **Batch Request Processing**:
   - NEVER loop individual curl/requests in shell scripts.
   - Submit all items in a single call to `POST /api/requests/batch`.
   - The backend worker automatically enforces 5 concurrent requests limit and 10s cooldown.
   - Check aggregate completion using `GET /api/requests/batch-status?video_id=<VID>`.

5. **Entity Orientations**:
   - Characters / Figures: Use `PORTRAIT` orientation.
   - Locations / Backgrounds: Use `LANDSCAPE` orientation.

## 5. Veo3 Custom Models & Durations

Veo3 extensions patch `VIDEO_MODELS` with:
- Standard: `4s`, `6s`, `8s`
- Looping modes: `veo3_loop_4s`, `veo3_loop_6s`, `veo3_loop_8s`
- Crop & Aspect ratio coordinates supported dynamically via FlowClient patches.

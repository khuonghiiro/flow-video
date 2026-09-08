# Flow Video Workspace — Master Agent Guide

Welcome to **flow-video** workspace. This repository orchestrates AI video production via Google Flow API, Chrome Extension bridge, Python FastAPI backend, and React Dashboard UI.

## Project Structure Overview

```
flow-video/
├── _setup_env.bat        # Root environment setup (Python venv, npm install, sync skills)
├── _start.bat            # Root launcher: starts Dashboard UI & Veo3 Backend Server
├── agent-veo3/           # Veo3 advanced enhancements & extension layer
│   ├── .venv/            # Python virtual environment
│   ├── agent/            # Veo3 FastAPI entrypoint, flowkit_loader & extension_patcher
│   ├── extension/        # Chrome Extension (MV3)
│   ├── scripts/          # Automation pipelines & test scripts
│   └── flow_agent.db     # SQLite database for projects, scenes & operations
├── flowkit/              # Upstream FlowKit Core engine
│   ├── agent/            # Core backend services, FlowClient & worker runner
│   ├── dashboard/        # React 19 + Vite + TailwindCSS v4 Dashboard
│   └── skills/           # AI Tool skills definitions (fk-*.md)
└── .agents/              # Workspace rules and custom agent skills
    ├── rules/            # Code modularity, coding standards, workflow rules
    └── skills/           # code-modularity-standards, flow-video-workflow
```

## Quick Reference & Ports

- **Agent Backend**: `http://127.0.0.1:8100` (FastAPI)
- **Extension Bridge**: `ws://127.0.0.1:9222` (WebSocket Server)
- **Dashboard UI**: `http://localhost:5173` (Vite dev server)
- **Health Check**: `GET http://127.0.0.1:8100/health` (verify `extension_connected: true`)

## Key Operational Rules

1. **Media IDs**: Always UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`), never base64.
2. **Scene Prompts**: Action & camera motion ONLY; never re-describe character appearance.
3. **Batch Requests**: Always submit through `POST /api/requests/batch`, server enforces 5 concurrent requests & 10s cooldown.
4. **Code Limits**: Target 150-500 lines per file, strictly under 800-1000 lines max. Methods under 50-80 lines.
5. **Non-invasive Patching**: Keep `flowkit/` core intact; apply Veo3 features via `agent-veo3/agent/extension_patcher.py`.

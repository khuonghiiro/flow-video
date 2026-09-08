---
name: code-modularity-standards
description: Enforces file length limits (max 800-1000 lines), method limits (max 50-80 lines), and clean multi-layered modular architecture across Python (FastAPI), TypeScript/React (Vite Dashboard), and Chrome Extension (MV3).
---

# Code Modularity & Line Limit Standards for Flow Video

When editing, refactoring, or creating new files in this workspace, you MUST adhere to the following standards:

## 1. Hard File Size Limits
- **Optimal Size**: 150 – 500 lines per file.
- **Maximum Ceiling**: **800 – 1,000 lines**. Under NO circumstances should any file exceed 1,000 lines.
- **Action Required**: When a file approaches 800 lines, immediately identify distinct functional domains and extract them into dedicated sub-modules.

## 2. Function & Method Size Limit
- Functions and methods must stay within **50 – 80 lines**.
- Extract internal loops, complex transformations, and helper algorithms into descriptive private helper functions.

## 3. Technology-Specific Modular Patterns

### Python Backend (`agent/`):
- `config.py`: Port, API hosts, model registry, directory paths.
- `models/`: Pydantic input/output schemas and data transfer objects.
- `api/`: Route handlers grouped by entity/feature (projects, scenes, media, operations).
- `services/`: Core business logic, FlowClient RPCs, batch worker runner, post-processing ffmpeg.
- `db/`: SQLite schema, migration helpers, async CRUD repository functions.
- `utils/`: Common helpers (file I/O, prompt parser, media url helpers).

### Dashboard Frontend (`flowkit/dashboard/`):
- `src/components/`: Reusable, focused UI elements under 300 lines each.
- `src/hooks/`: Stateful logic, query hooks, WebSocket connection handlers.
- `src/types/`: TypeScript definitions mirroring backend schemas.
- `src/lib/`: API clients, formatting utilities, theme helpers.

### Chrome Extension (`extension/`):
- Clean separation between background service worker, content scripts, and popup UI.
- Do not overload a single script with all message listeners and RPC clients.

## 4. Verification Check
Before concluding any task:
1. Verify line counts of modified or created files.
2. Confirm 0 syntax / compilation errors.

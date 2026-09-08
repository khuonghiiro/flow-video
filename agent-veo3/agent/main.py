"""Agent Veo3 Entrypoint - Bootstraps FlowKit Core and applies Veo3 Enhancements.

When uvicorn launches 'agent.main:app', this module:
1. Bootstraps upstream FlowKit into sys.path and agent namespace
2. Dynamically loads the upstream FastAPI application instance
3. Applies non-invasive Veo3 patches (models, FlowClient, worker parsing, WebSocket heartbeat)
4. Mounts Veo3 extension routes (pipelines, browser bridge, cancel-all)
"""
import importlib.util
import logging
import sys
from pathlib import Path

# Step 1: Bootstrap upstream flowkit
from agent.flowkit_loader import FLOWKIT_DIR, bootstrap_flowkit

bootstrap_flowkit()

logger = logging.getLogger("veo3_main")

# Step 2: Load upstream flowkit FastAPI app instance
flowkit_main_path = FLOWKIT_DIR / "agent" / "main.py"
if not flowkit_main_path.exists():
    raise FileNotFoundError(f"Upstream main.py not found at: {flowkit_main_path}")

spec = importlib.util.spec_from_file_location("flowkit_core_main", str(flowkit_main_path))
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load spec for: {flowkit_main_path}")

core_main = importlib.util.module_from_spec(spec)
# Register in sys.modules to prevent redundant re-executions
sys.modules["flowkit_core_main"] = core_main
spec.loader.exec_module(core_main)

app = core_main.app

# Step 3: Apply Veo3 enhancements & mount extension routes
from agent.extension_patcher import apply_all_patches

apply_all_patches(app)

logger.info("Agent Veo3 server initialized on FlowKit core engine.")

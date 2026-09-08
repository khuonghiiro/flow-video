"""FlowKit Loader - Bridges upstream flowkit core with agent-veo3 extensions.

Enables agent-veo3 to dynamically inherit, wrap, and extend flowkit
without merge conflicts or direct code mutations in the upstream repository.
"""
import importlib
import logging
import os
import pathlib
import sys

logger = logging.getLogger("flowkit_loader")

_CURRENT_DIR = pathlib.Path(__file__).resolve().parent
_VEO3_ROOT = _CURRENT_DIR.parent
_DEFAULT_FLOWKIT = _VEO3_ROOT.parent / "flowkit"

FLOWKIT_DIR = pathlib.Path(os.environ.get("FLOWKIT_DIR", _DEFAULT_FLOWKIT)).resolve()


def _bridge_subpackage(sub_name: str):
    """Ensure both flowkit and agent-veo3 directories are in agent.<sub_name>.__path__."""
    fk_sub = FLOWKIT_DIR / "agent" / sub_name
    veo_sub = _CURRENT_DIR / sub_name

    try:
        mod = importlib.import_module(f"agent.{sub_name}")
        if hasattr(mod, "__path__"):
            # Upstream flowkit takes precedence
            fk_str = str(fk_sub)
            if fk_sub.is_dir() and fk_str not in mod.__path__:
                mod.__path__.insert(0, fk_str)
            # Veo3 extensions are present as fallback/enhancement
            veo_str = str(veo_sub)
            if veo_sub.is_dir() and veo_str not in mod.__path__:
                mod.__path__.append(veo_str)
    except Exception as exc:
        logger.debug("Subpackage bridge for %s skipped: %s", sub_name, exc)


def bootstrap_flowkit() -> pathlib.Path:
    """Bootstrap upstream flowkit into sys.path and extend agent namespace.

    Returns:
        pathlib.Path: Absolute path to the detected flowkit directory.
    """
    if not FLOWKIT_DIR.exists() or not FLOWKIT_DIR.is_dir():
        raise FileNotFoundError(
            f"[FlowKit Loader] Upstream flowkit directory not found at: {FLOWKIT_DIR}\n"
            f"Please ensure flowkit is cloned alongside agent-veo3 or set FLOWKIT_DIR."
        )

    flowkit_str = str(FLOWKIT_DIR)
    if flowkit_str not in sys.path:
        sys.path.insert(0, flowkit_str)
        logger.info("Added upstream flowkit to sys.path: %s", flowkit_str)

    veo3_str = str(_VEO3_ROOT)
    if veo3_str not in sys.path:
        sys.path.insert(1, veo3_str)

    # 1. Bridge the root 'agent' package
    import agent
    upstream_agent_dir = str(FLOWKIT_DIR / "agent")
    if upstream_agent_dir not in agent.__path__:
        agent.__path__.insert(0, upstream_agent_dir)
    veo3_agent_dir = str(_CURRENT_DIR)
    if veo3_agent_dir not in agent.__path__:
        agent.__path__.append(veo3_agent_dir)

    # 2. Bridge all subpackages so modules in either location resolve cleanly
    subpackages = ["services", "api", "worker", "sdk", "models", "db", "utils"]
    for sub in subpackages:
        _bridge_subpackage(sub)

    logger.info("Successfully bridged agent namespaces across flowkit and agent-veo3")
    return FLOWKIT_DIR


# Auto bootstrap upon import
try:
    bootstrap_flowkit()
except Exception as _exc:
    logger.warning("Auto bootstrap deferred: %s", _exc)

"""Utility CLI script to upload male and female mannequin pose guides to a Flow project.

Usage:
    python scripts/upload_mannequins.py --project-id <PROJECT_ID> [--gender male|female|both]
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_DIR = SCRIPT_DIR.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from agent.services.flow_client import get_flow_client
from agent.services.mannequin_service import (
    ensure_all_mannequins_for_project,
    get_mannequin_path,
    upload_mannequin_reference,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("upload_mannequins")


async def main():
    parser = argparse.ArgumentParser(description="Upload Mannequin Angle Guides to Google Flow")
    parser.add_argument("--project-id", required=True, help="Google Flow Project UUID")
    parser.add_argument("--gender", choices=["male", "female", "both"], default="both", help="Gender set to upload")
    args = parser.parse_args()

    client = get_flow_client()
    if not client.connected:
        logger.info("Connecting to Flow Extension WebSocket...")
        # attempt connection
        for _ in range(5):
            if client.connected:
                break
            await asyncio.sleep(1)

    if not client.connected:
        logger.error("Flow Extension is not connected on ws://127.0.0.1:8100. Please start Flow extension.")
        sys.exit(1)

    genders = ["male", "female"] if args.gender == "both" else [args.gender]
    summary = {}

    for g in genders:
        logger.info("Uploading %s mannequin guides to project %s...", g.upper(), args.project_id)
        res = await ensure_all_mannequins_for_project(client, args.project_id, g)
        summary[g] = res

    print("\n" + "=" * 50)
    print("MANNEQUIN UPLOAD SUMMARY:")
    print(json.dumps(summary, indent=2))
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

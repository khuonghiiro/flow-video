"""Download existing completed media files from Google Flow to local disk."""
import asyncio
import json
import logging
import os
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("downloader")

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))


async def fetch_one(session: aiohttp.ClientSession, mid: str, path: str) -> bool:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    url_red = f"http://127.0.0.1:8100/api/flow/media-redirect-url/{mid}"
    try:
        async with session.get(url_red, timeout=15) as r:
            d = await r.json()
        u = d.get("data", {}).get("url")
        if not u:
            logger.warning("Failed to get URL for %s", mid)
            return False
        async with session.get(u, timeout=90) as vr:
            content = await vr.read()
        if len(content) < 1000:
            logger.warning("File too small for %s (%d bytes)", mid, len(content))
            return False
        with open(path, "wb") as f:
            f.write(content)
        logger.info("Saved %s (Size: %d bytes)", os.path.basename(path), len(content))
        return True
    except Exception as e:
        logger.error("Download error for %s: %s", mid, e)
        return False


async def download_character_files(character_key: str):
    char_dir = os.path.join(OUTPUT_DIR, character_key)
    meta_path = os.path.join(char_dir, "character_meta.json")
    if not os.path.exists(meta_path):
        logger.error("Metadata not found: %s", meta_path)
        return

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    targets = []
    # 1. Base angles
    for ang in ["0", "45", "90", "135", "180"]:
        ang_key = f"angle_{ang}"
        info = meta.get(ang_key, {})
        mid = info.get("media_id")
        file_rel = info.get("file", f"angle_{ang}.png")
        path = os.path.join(char_dir, file_rel)
        if mid and (not os.path.exists(path) or os.path.getsize(path) < 1000):
            targets.append((mid, path))

    # 2. Actions
    for folder, angles in meta.get("actions", {}).items():
        for ang, info in angles.items():
            if info.get("status") in ("COMPLETED", "SUCCESSFUL"):
                file_rel = info.get("file")
                path = os.path.join(char_dir, file_rel)
                if not os.path.exists(path) or os.path.getsize(path) < 1000:
                    targets.append((info.get("media_id"), path))

    logger.info("Found %d missing files to download for %s", len(targets), character_key)
    if not targets:
        return

    async with aiohttp.ClientSession() as s:
        tasks = [fetch_one(s, mid, path) for mid, path in targets]
        results = await asyncio.gather(*tasks)
        logger.info("Downloaded %d/%d files successfully.", sum(results), len(targets))


if __name__ == "__main__":
    import sys
    char = sys.argv[1] if len(sys.argv) > 1 else "diep-thanh-lam"
    asyncio.run(download_character_files(char))

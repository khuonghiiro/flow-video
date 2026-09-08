import os
import sys
import json
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.generate_action_loop import ACTION_FOLDER_MAP, ANIMATION_PRIORITY_SEQUENCE, LOOP_ACTIONS

def get_mp4_duration(path: str) -> float:
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        return 0.0
    try:
        with open(path, "rb") as f:
            data = f.read()
        idx = data.find(b"mvhd")
        if idx != -1:
            v = data[idx + 4]
            if v == 0:
                ts, dur = struct.unpack(">II", data[idx + 16 : idx + 24])
            else:
                ts, dur = struct.unpack(">IQ", data[idx + 24 : idx + 36])
            return round(dur / ts, 2)
    except Exception:
        pass
    return 0.0

def sync_character(character_key: str = "han-lang-phong"):
    char_dir = os.path.join("output", character_key)
    meta_path = os.path.join(char_dir, "character_meta.json")
    if not os.path.exists(meta_path):
        print("meta_path not found:", meta_path)
        return

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    angles = ["0", "45", "90", "135", "180"]
    actions_dict = meta.setdefault("actions", {})

    total_synced = 0
    total_missing = 0

    for act in ANIMATION_PRIORITY_SEQUENCE:
        folder, label = ACTION_FOLDER_MAP.get(act, (act, act))
        act_entry = actions_dict.setdefault(folder, {})
        is_loop = act in LOOP_ACTIONS
        expected_dur = 4.0 if is_loop else 8.0

        for ang in angles:
            angle_key = f"angle_{ang}"
            vid_path = os.path.join(char_dir, folder, f"{act}_{ang}.mp4")
            dur = get_mp4_duration(vid_path)
            size = os.path.getsize(vid_path) if os.path.exists(vid_path) else 0

            # Only accept if duration matches expected (within 0.5s)
            if abs(dur - expected_dur) <= 0.5 and size > 1000:
                # Keep existing media_id if present
                existing_media_id = act_entry.get(angle_key, {}).get("media_id", "")
                act_entry[angle_key] = {
                    "media_id": existing_media_id,
                    "file": f"{folder}/{act}_{ang}.mp4",
                    "duration": expected_dur,
                    "resolution": "720x1280",
                    "size_bytes": size,
                    "status": "COMPLETED",
                }
                total_synced += 1
            else:
                # Remove stale entry if duration was wrong
                if angle_key in act_entry:
                    del act_entry[angle_key]
                total_missing += 1

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Synced character_meta.json for {character_key}:")
    print(f"  - Completed ({expected_dur}s): {total_synced}/80")
    print(f"  - Pending/Needing generation: {total_missing}/80")

if __name__ == "__main__":
    sync_character()

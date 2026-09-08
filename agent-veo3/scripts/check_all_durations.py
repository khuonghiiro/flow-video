import os
import sys
import struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.generate_action_loop import ACTION_FOLDER_MAP, ANIMATION_PRIORITY_SEQUENCE, LOOP_ACTIONS

char_dir = "output/han-lang-phong"
angles = ["0", "45", "90", "135", "180"]

def get_dur(path):
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        return 0.0
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
    return 0.0

needs_work = []
for act in ANIMATION_PRIORITY_SEQUENCE:
    folder, _ = ACTION_FOLDER_MAP.get(act, (act, act))
    durs = []
    is_loop = act in LOOP_ACTIONS
    expected = 4.0 if is_loop else 8.0
    for ang in angles:
        p = os.path.join(char_dir, folder, f"{act}_{ang}.mp4")
        d = get_dur(p)
        durs.append(f"{ang}:{d}s")
        if abs(d - expected) > 0.5:
            needs_work.append((act, ang, d, expected))
    exp_str = f"{expected:.1f}s"
    print(f"{act:20s} [Exp: {exp_str:4s}]: {' '.join(durs)}")

print(f"\nTotal videos needing generation/update: {len(needs_work)}")
for act, ang, d, exp in needs_work:
    print(f"  - {act} {ang}°: current={d}s, expected={exp}s")

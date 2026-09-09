"""
Sync & Audit Skills with OOP Override Hierarchy.
Ensures agent-veo3/skills (derived) overrides flowkit/skills (base) seamlessly.
"""

from pathlib import Path
import sys

# Reconfigure console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
FLOWKIT_SKILLS = ROOT / "flowkit" / "skills"
VEO3_SKILLS = ROOT / "agent-veo3" / "skills"
VEO3_SKILLS_VI = ROOT / "agent-veo3" / "skills_vi"


def get_active_skills() -> dict[str, dict]:
    """
    Quét và phân giải danh sách kỹ năng theo mô hình kế thừa OOP:
    agent-veo3/skills (Override) > flowkit/skills (Base)
    """
    skills_map = {}

    # 1. Nạp lớp cha (Base): flowkit/skills
    if FLOWKIT_SKILLS.exists():
        for f in sorted(FLOWKIT_SKILLS.glob("fk-*.md")):
            skills_map[f.name] = {
                "name": f.name,
                "layer": "flowkit (base)",
                "path": f,
                "overridden_by": None,
                "has_vi": False,
            }

    # 2. Nạp lớp con (Override): agent-veo3/skills
    if VEO3_SKILLS.exists():
        for f in sorted(VEO3_SKILLS.glob("fk-*.md")):
            if f.name in skills_map:
                skills_map[f.name] = {
                    "name": f.name,
                    "layer": "agent-veo3 (OVERRIDE)",
                    "path": f,
                    "overridden_by": "agent-veo3",
                    "has_vi": False,
                }
            else:
                skills_map[f.name] = {
                    "name": f.name,
                    "layer": "agent-veo3 (NEW)",
                    "path": f,
                    "overridden_by": None,
                    "has_vi": False,
                }

    # 3. Kiểm tra bản Tiếng Việt trong agent-veo3/skills_vi
    if VEO3_SKILLS_VI.exists():
        for f in VEO3_SKILLS_VI.glob("fk-*.md"):
            if f.name in skills_map:
                skills_map[f.name]["has_vi"] = True

    return skills_map


def audit_report():
    print("=" * 80)
    print("      SKILL RESOLUTION AUDIT (OOP HIERARCHY: agent-veo3 > flowkit)")
    print("=" * 80)

    skills = get_active_skills()
    overridden = [s for s in skills.values() if s["overridden_by"] == "agent-veo3"]
    new_veo3 = [s for s in skills.values() if s["layer"] == "agent-veo3 (NEW)"]
    base_only = [s for s in skills.values() if s["layer"] == "flowkit (base)"]

    print(f"\n[+] Tổng số kỹ năng khả dụng: {len(skills)}")
    print(f"    - Kỹ năng ghi đè (Overridden by agent-veo3): {len(overridden)}")
    print(f"    - Kỹ năng mới độc quyền (agent-veo3 only): {len(new_veo3)}")
    print(f"    - Kỹ năng cơ sở nguyên bản (flowkit base): {len(base_only)}")

    if overridden:
        print("\n[*] CÁC KỸ NĂNG ĐƯỢC GHI ĐÈ BỞI AGENT-VEO3 (Ưu tiên logic mới):")
        for s in overridden:
            vi_tag = " [Có Tiếng Việt]" if s["has_vi"] else ""
            print(f"    - {s['name']:<25} ➔ {s['path'].relative_to(ROOT)}{vi_tag}")

    if new_veo3:
        print("\n[*] CÁC KỸ NĂNG MỚI TRONG AGENT-VEO3:")
        for s in new_veo3:
            vi_tag = " [Có Tiếng Việt]" if s["has_vi"] else ""
            print(f"    - {s['name']:<25} ➔ {s['path'].relative_to(ROOT)}{vi_tag}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    audit_report()

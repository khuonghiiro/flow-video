"""Sync FlowKit Upstream - Pull latest core code from author repository.

Safely updates upstream flowkit while keeping agent-veo3 enhancements intact.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOWKIT_DIR = (ROOT.parent / "flowkit").resolve()


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str]:
    res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.returncode, (res.stdout + res.stderr).strip()


def sync():
    print("=" * 70)
    print("        DONG BO FLOWKIT GOC TU TAC GIA (UPSTREAM SYNC)")
    print("=" * 70)
    print(f"[*] Thu muc FlowKit goc: {FLOWKIT_DIR}")

    if not FLOWKIT_DIR.exists():
        print(f"[LOI] Khong tim thay thu muc flowkit tai: {FLOWKIT_DIR}")
        sys.exit(1)

    # 1. Check git remote
    code, out = run_cmd(["git", "remote", "-v"], FLOWKIT_DIR)
    if code != 0 or not out:
        print("[CANH BAO] Thu muc flowkit khong phai la mot Git repo hop le.")
    else:
        print(f"[*] Remote repository:\n    {out.splitlines()[0]}")

    # 2. Git fetch and pull
    print("[*] Dang cap nhat ma nguon tu GitHub (git pull origin main)...")
    code, out = run_cmd(["git", "pull", "origin", "main"], FLOWKIT_DIR)
    print(f"    {out}")
    if code != 0:
        print("[LOI] git pull that bai! Vui long kiem tra ket noi mang hoac xung dot.")
        sys.exit(1)

    # 3. Check requirements
    req_file = FLOWKIT_DIR / "requirements.txt"
    if req_file.exists():
        venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
        py_exec = str(venv_py) if venv_py.exists() else sys.executable
        print(f"[*] Kiem tra dependencies ({req_file.name})...")
        code, out = run_cmd([py_exec, "-m", "pip", "install", "-r", str(req_file)], ROOT)
        if code == 0:
            print("    Dependencies hop le va da san sang.")
        else:
            print(f"    [CANH BAO] pip install: {out}")

    # 4. Verify agent-veo3 runtime compatibility
    print("[*] Kiem tra tuong thich runtime giua flowkit va agent-veo3...")
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    py_exec = str(venv_py) if venv_py.exists() else sys.executable
    test_code = (
        "import sys; "
        f"sys.path.insert(0, r'{ROOT}'); "
        "from agent.flowkit_loader import bootstrap_flowkit; bootstrap_flowkit(); "
        "from agent.main import app; "
        "print(f'[OK] Server app san sang voi {len(app.routes)} endpoints!')"
    )
    code, out = run_cmd([py_exec, "-c", test_code], ROOT)
    print(f"    {out}")
    if code == 0 and "[OK]" in out:
        print("=" * 70)
        print("   [THANH CONG] FlowKit da duoc cap nhat! Agent-Veo3 hoat dong hoan hao!")
        print("=" * 70)
    else:
        print("[CANH BAO] Co loi khi kiem tra runtime sau khi cap nhat.")


if __name__ == "__main__":
    sync()

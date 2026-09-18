"""
Automated Version Bump and Git Push Script.
Fulfills user requirements:
- Bumps version on every edit/feature (e.g. 1.0.0 -> 1.0.1)
- Automatically commits and pushes to GitHub
- Never zips unless explicitly requested
"""

import sys
import subprocess
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from version import bump_version, get_version


def run_git(cmd: list):
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"Git warning/error: {res.stderr.strip()}", file=sys.stderr)
    return res.returncode == 0


def bump_and_push(commit_message: str = "Update features and stability improvements", part: str = "patch"):
    old_version = get_version()
    new_version = bump_version(part)
    print(f"🔄 Đã nâng phiên bản: v{old_version} ➔ v{new_version}")

    print("📦 Đang chuẩn bị Git commit...")
    run_git(["git", "add", "."])
    
    full_message = f"v{new_version}: {commit_message}"
    run_git(["git", "commit", "-m", full_message])

    print(f"🚀 Đang tự động đẩy lên GitHub (origin main)...")
    success = run_git(["git", "push", "origin", "main"])
    if success:
        print(f"✅ Đã đẩy thành công phiên bản v{new_version} lên GitHub!")
    else:
        print("⚠️ Không thể đẩy trực tiếp lên GitHub (vui lòng kiểm tra quyền truy cập git credentials/token).")

    return new_version


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Auto update"
    bump_and_push(msg)

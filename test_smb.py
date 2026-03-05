#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence, Tuple


def build_env() -> dict:
    env = os.environ.copy()
    env["CLICOLOR_FORCE"] = "1"
    env["FORCE_COLOR"] = "1"
    env["TERM"] = "xterm-256color"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"
    return env


def run_mock(nxcs, output: Path) -> int:
    thai_folder = "\u0e42\u0e1f\u0e25\u0e40\u0e14\u0e2d\u0e23\u0e4c\u0e25\u0e31\u0e1a"
    thai_status = "\u0e2d\u0e48\u0e32\u0e19/\u0e40\u0e02\u0e35\u0e22\u0e19\u0e44\u0e14\u0e49"
    sample = (
        "\x1b[34mSMB\x1b[0m         10.0.61.62   445   HOST01\n"
        "\x1b[32m[+]\x1b[0m auth ok\n"
        "\x1b[33mShare\x1b[0m       \x1b[33mPermissions\x1b[0m\n"
        "Users        READ\n"
        f"{thai_folder}   READ,WRITE  ({thai_status})\n"
    )
    nxcs.text_to_image_color(sample, str(output))
    if not output.exists() or output.stat().st_size == 0:
        print("FAIL: mock image not created")
        return 1
    print(f"PASS mock -> {output.resolve()}")
    return 0


def resolve_nxc_runner(args: argparse.Namespace) -> Tuple[Optional[Sequence[str]], Optional[str]]:
    # Prefer local NetExec source repo when provided.
    if args.nxc_repo:
        repo = Path(args.nxc_repo).resolve()
        if not repo.exists():
            return None, f"FAIL: --nxc-repo not found: {repo}"

        # Support both repo root (.../NetExec) and package dir (.../NetExec/nxc).
        if repo.name.lower() == "nxc" and (repo / "netexec.py").exists():
            repo = repo.parent

        if not (repo / "nxc" / "netexec.py").exists():
            return None, f"FAIL: nxc/netexec.py not found in repo: {repo}"
        return [sys.executable, "-m", "nxc.netexec"], str(repo)

    # Fallback to global nxc command in PATH.
    if shutil.which("nxc"):
        return ["nxc"], None

    return None, (
        "FAIL: nxc not found in PATH\n"
        "Install helper: powershell -ExecutionPolicy Bypass -File .\\install_nxc.ps1\n"
        "Or use local source repo: python test_smb.py --mode live --nxc-repo \"D:\\git project\\NetExec\" --target 127.0.0.1 --port 1445 --shares"
    )


def run_live(nxcs, output: Path, args: argparse.Namespace) -> int:
    runner, runner_cwd = resolve_nxc_runner(args)
    if not runner:
        print(runner_cwd)
        return 2
    if not args.target:
        print("FAIL: --target is required for --mode live")
        return 2

    cmd = list(runner) + ["smb", args.target]
    if args.user:
        cmd += ["-u", args.user]
    if args.password:
        cmd += ["-p", args.password]
    if "--shares" not in args.extra:
        cmd += ["--shares"]
    if args.extra:
        cmd += args.extra

    env = build_env()
    result = subprocess.run(cmd, capture_output=True, text=False, env=env, cwd=runner_cwd)
    raw_output = nxcs.decode_bytes(result.stdout) + nxcs.decode_bytes(result.stderr)
    if not raw_output.strip():
        print("FAIL: empty output from nxc")
        return 1
    if not args.no_thai_probe:
        raw_output += (
            "\n"
            "\x1b[34m[*]\x1b[0m Thai probe line for rendering test\n"
            "โฟลเดอร์ทดสอบไทย  READ,WRITE  (อ่าน/เขียนได้)\n"
        )

    nxcs.text_to_image_color(raw_output, str(output))
    if not output.exists() or output.stat().st_size == 0:
        print("FAIL: live image not created")
        return 1

    print(f"PASS live -> {output.resolve()}")
    print(f"Command: {' '.join(cmd)}")
    print("Verify manually: Thai should be readable (not squares or mojibake).")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SMB rendering test for nxcs (mock and live nxc modes)"
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "live"],
        default="mock",
        help="mock: no network call, live: execute nxc smb command",
    )
    parser.add_argument("--target", help="SMB target IP/hostname for live mode")
    parser.add_argument(
        "--nxc-repo",
        default=os.environ.get("NXC_REPO"),
        help="Path to local NetExec repo (use source mode: python -m nxc)",
    )
    parser.add_argument("--user", help="Username for live mode")
    parser.add_argument("--password", help="Password for live mode")
    parser.add_argument(
        "--output",
        default="smb_test_output.png",
        help="Output image file path (default: smb_test_output.png)",
    )
    parser.add_argument(
        "--no-thai-probe",
        action="store_true",
        help="Do not append Thai probe lines in live mode",
    )
    args, extra = parser.parse_known_args()
    args.extra = extra
    return args


def main() -> int:
    args = parse_args()
    try:
        import code as nxcs
    except ModuleNotFoundError as exc:
        if exc.name == "PIL":
            print("Missing dependency: Pillow")
            print("Install with: python -m pip install pillow")
            return 2
        raise

    output = Path(args.output)
    if args.mode == "mock":
        return run_mock(nxcs, output)
    return run_live(nxcs, output, args)


if __name__ == "__main__":
    sys.exit(main())

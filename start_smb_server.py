#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start a local SMB server for dev/testing."
    )
    parser.add_argument(
        "--share-name",
        default="TESTSHARE",
        help="SMB share name (default: TESTSHARE)",
    )
    parser.add_argument(
        "--path",
        default="smb_share",
        help="Directory to expose as SMB share (default: ./smb_share)",
    )
    parser.add_argument(
        "--listen-ip",
        default="0.0.0.0",
        help="Bind IP (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=445,
        help="SMB port (default: 445)",
    )
    parser.add_argument("--username", help="Optional SMB username")
    parser.add_argument("--password", help="Optional SMB password")
    parser.add_argument(
        "--no-smb2",
        action="store_true",
        help="Disable SMB2 support (default: SMB2 enabled)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    share_path = Path(args.path).resolve()
    share_path.mkdir(parents=True, exist_ok=True)

    try:
        from impacket import smbserver
        from impacket.ntlm import compute_lmhash, compute_nthash
    except ModuleNotFoundError:
        print("Missing dependency: impacket")
        print("Install with: python -m pip install impacket")
        return 2

    try:
        server = smbserver.SimpleSMBServer(
            listenAddress=args.listen_ip, listenPort=args.port
        )
    except PermissionError:
        print(f"Permission denied binding {args.listen_ip}:{args.port}")
        print("On Windows, port 445 is usually reserved by the OS SMB service.")
        print("Try: python start_smb_server.py --port 1445")
        return 1
    except OSError as exc:
        print(f"Failed to bind {args.listen_ip}:{args.port} -> {exc}")
        print("Try a different port, e.g. --port 1445")
        return 1
    server.addShare(args.share_name, str(share_path), "NXCS test SMB share")
    server.setSMB2Support(not args.no_smb2)

    if args.username or args.password:
        if not (args.username and args.password):
            print("Both --username and --password are required together.")
            return 2
        lmhash = compute_lmhash(args.password)
        nthash = compute_nthash(args.password)
        server.addCredential(args.username, 0, lmhash, nthash)

    print("SMB server started")
    print(f"Share Name : {args.share_name}")
    print(f"Share Path : {share_path}")
    print(f"Listen     : {args.listen_ip}:{args.port}")
    if args.username:
        print(f"Auth       : {args.username}/********")
    else:
        print("Auth       : anonymous")
    print("Press Ctrl+C to stop")

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except PermissionError:
        print("Permission denied on selected port.")
        print("Try running as admin/root or use a higher port with --port.")
        return 1
    except OSError as exc:
        print(f"OS error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

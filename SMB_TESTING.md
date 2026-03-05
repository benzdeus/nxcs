# SMB Testing Guide (Dev)

## 1) Start Local SMB Server

Run in `D:\git project\nxcs`:

```powershell
py .\start_smb_server.py --port 1445 --share-name TESTSHARE --path .\smb_share --username testuser --password testpass --no-smb2
```

Keep this terminal open.

## 2) Verify NetExec Directly

Run in another terminal:

```powershell
py -3.12 -m nxc.netexec smb 127.0.0.1 --port 1445 -u testuser -p testpass --shares
```

If this works, NetExec/auth is OK.

## 3) Run NXCS SMB Test Script

Equivalent test command for `test_smb.py`:

```powershell
py -3.12 .\test_smb.py --mode live --nxc-repo "D:\git project\NetExec" --target 127.0.0.1 --user testuser --password testpass --port 1445
```

Output image default: `smb_test_output.png`

## 4) Validate Result

- Open `smb_test_output.png`
- Confirm Thai text is readable (not square boxes)
- Confirm ANSI colors are still rendered

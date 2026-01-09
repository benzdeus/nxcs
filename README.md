# NXCS (NetExec Screenshotter) 📸

**NXCS** is a wrapper tool for [NetExec (nxc)](https://github.com/Pennyw0rth/NetExec) that automates the process of scanning and capturing output results as PNG images. It supports full ANSI colors, multi-threading, and automatically organizes results into folders.

## ✨ Features
- **Auto-Screenshot:** Converts NetExec output into high-quality PNG images.
- **Color Support:** Preserves terminal colors (e.g., green for success, red for failure).
- **Subnet Support:** Automatically scans a subnet (e.g., `/24`), discovers live hosts, and generates individual screenshots for each IP.
- **Folder Organization:** Creates directories for each subnet scan.
- **Multi-threaded:** Fast parallel processing for multiple hosts.
- **Cross-Platform:** Works on Kali Linux and macOS.

---

## 🚀 Installation

### 1. Prerequisites
Ensure you have Python 3 and NetExec installed.

```bash
# Install NetExec (if not already installed)
pipx install netexec
# OR
pip install netexec
```

### 2. Install Dependencies
Install the required Python library for image generation.

```bash
pip install pillow
```

### 3. Setup Script
Download the script and move it to your system path.

```bash
# 1. Create the file (paste the code)
sudo nano /usr/local/bin/nxcs

# 2. Make it executable
sudo chmod +x /usr/local/bin/nxcs
```

---

## 💻 Usage

You can use `nxcs` exactly like you use `nxc`. Just replace `nxc` with `nxcs`.

### Single Host Scan
Generates a single image file `192.168.1.10.png` in the current directory.

```bash
nxcs smb 192.168.1.10 -u 'admin' -p 'password' --shares
```

### Subnet Scan (The Killer Feature 🔥)
1. Automatically discovers live hosts in the subnet.
2. Creates a folder named `192.168.1.0_24`.
3. Saves individual PNGs for each live host inside that folder.

```bash
nxcs smb 192.168.1.0/24 -u 'admin' -p 'password' --shares
```

---

## 🍎 macOS Users Note

If you are running this on macOS:
1. Ensure you have installed NetExec properly and it is in your PATH.
2. The script automatically looks for macOS system fonts (`Menlo`, `Monaco`). If the output font looks strange, ensure you have a monospaced font installed.

---

## 🛠 Troubleshooting

**Error: `ImageMagick not found` or Font issues**
> NXCS uses Python's `Pillow` library now, so ImageMagick is no longer required. If fonts are missing, it will fallback to a default (ugly) font. Install `fonts-dejavu` on Linux for best results: `sudo apt install fonts-dejavu`.

**Error: `nxc: command not found`**
> Ensure NetExec is installed and accessible in your terminal. Try running `nxc --version` to verify.
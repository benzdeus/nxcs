#!/usr/bin/env python3
import sys
import subprocess
import re
import os
import ipaddress
import concurrent.futures
import locale
from PIL import Image, ImageDraw, ImageFont

# --- Config ---
MAX_THREADS = 20
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Color Mapping (ANSI to RGB) ---
ANSI_COLORS = {
    '0':  (220, 220, 220), # Default
    '30': (0, 0, 0),       # Black
    '31': (255, 85, 85),   # Red
    '32': (80, 250, 123),  # Green
    '33': (241, 250, 140), # Yellow
    '34': (189, 147, 249), # Blue
    '35': (255, 121, 198), # Magenta
    '36': (139, 233, 253), # Cyan
    '37': (255, 255, 255), # White
    # Bright versions (90-97)
    '90': (98, 114, 164), '91': (255, 110, 110), '92': (105, 255, 148),
    '93': (255, 255, 165), '94': (214, 172, 255), '95': (255, 146, 223),
    '96': (164, 255, 255), '97': (255, 255, 255),
}
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
KNOWN_PROTOCOLS = {
    "SMB", "LDAP", "WINRM", "WMI", "SSH", "FTP", "MSSQL", "RDP", "NFS", "VNC", "HTTP", "RDP"
}

def contains_thai(text):
    return any("\u0E00" <= ch <= "\u0E7F" for ch in text)


def get_fonts():
    # Keep table alignment with monospaced fonts, and use a dedicated Thai font for Thai glyphs.
    mono_font_paths = [
        # Bundled monospace options (if provided)
        os.path.join(BASE_DIR, "fonts", "CascadiaMono.ttf"),
        os.path.join(BASE_DIR, "fonts", "JetBrainsMono-Regular.ttf"),
        # Windows
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\cour.ttf",
        r"C:\Windows\Fonts\CascadiaMono.ttf",
        # Linux / Kali
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/hack/Hack-Regular.ttf",
        # macOS
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/Library/Fonts/Courier New.ttf",
    ]
    thai_font_paths = [
        # Bundled with this repository (portable Thai support)
        os.path.join(BASE_DIR, "fonts", "NotoSansThai-Regular.ttf"),
        os.path.join(BASE_DIR, "fonts", "NotoSansThai-Variable.ttf"),
        os.path.join(BASE_DIR, "fonts", "NotoSansThaiLooped-Variable.ttf"),
        # Optional bundled Thai monospaced font
        os.path.join(BASE_DIR, "fonts", "TlwgMono.ttf"),
        os.path.join(BASE_DIR, "fonts", "tlwgmono.ttf"),
        # Windows
        r"C:\Windows\Fonts\LeelawUI.ttf",
        r"C:\Windows\Fonts\LeelUIsl.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\THSarabunNew.ttf",
        # Linux / Kali
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThaiUI-Regular.ttf",
        "/usr/share/fonts/truetype/thai-tlwg/Garuda.ttf",
        "/usr/share/fonts/truetype/thai-tlwg/TlwgMono.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Thonburi.ttf",
        "/System/Library/Fonts/Supplemental/SukhumvitSet.ttc",
    ]
    mono_font = None
    thai_font = None
    for p in mono_font_paths:
        if os.path.exists(p):
            try:
                mono_font = ImageFont.truetype(p, 14)
                break
            except Exception:
                continue
    for p in thai_font_paths:
        if os.path.exists(p):
            try:
                thai_font = ImageFont.truetype(p, 14)
                break
            except Exception:
                continue
    if mono_font is None:
        mono_font = ImageFont.load_default()
    if thai_font is None:
        thai_font = mono_font
    return mono_font, thai_font


def decode_bytes(data):
    # Try common encodings in order; cp874 covers Thai legacy codepages.
    if data is None:
        return ""
    encodings = ["utf-8", "cp874", locale.getpreferredencoding(False)]
    for enc in encodings:
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def apply_fallback_ansi(text):
    # NetExec via subprocess on Windows often emits plain text without ANSI.
    colorized = []
    for line in text.splitlines():
        updated = line
        has_ansi = bool(ANSI_ESCAPE_RE.search(updated))

        if not has_ansi:
            protocol_match = re.match(r"^([A-Z0-9]{2,10})(\s+)", updated)
            if protocol_match and protocol_match.group(1) in KNOWN_PROTOCOLS:
                proto = protocol_match.group(1)
                spacing = protocol_match.group(2)
                updated = f"\x1b[34m{proto}\x1b[0m{spacing}" + updated[protocol_match.end():]

            updated = re.sub(r"(\[\+\])", lambda m: f"\x1b[32m{m.group(1)}\x1b[0m", updated)
            updated = re.sub(r"(\[-\])", lambda m: f"\x1b[31m{m.group(1)}\x1b[0m", updated)
            updated = re.sub(r"(\[\*\])", lambda m: f"\x1b[34m{m.group(1)}\x1b[0m", updated)
            updated = re.sub(r"\b(READ,WRITE|READ|WRITE)\b", lambda m: f"\x1b[33m{m.group(1)}\x1b[0m", updated)

        colorized.append(updated)
    return "\n".join(colorized)

def is_thai_char(ch):
    return "\u0E00" <= ch <= "\u0E7F"


def split_script_runs(text):
    if not text:
        return []
    runs = []
    buf = [text[0]]
    current_is_thai = is_thai_char(text[0])
    for ch in text[1:]:
        ch_is_thai = is_thai_char(ch)
        if ch_is_thai == current_is_thai:
            buf.append(ch)
        else:
            runs.append(("".join(buf), current_is_thai))
            buf = [ch]
            current_is_thai = ch_is_thai
    runs.append(("".join(buf), current_is_thai))
    return runs


def draw_colored_text(draw, text, mono_font, thai_font, x_start, y_start):
    parts = re.split(r'(\x1b\[[0-9;]*m)', text)
    current_color = ANSI_COLORS['0']
    x = x_start
    for part in parts:
        if part.startswith('\x1b['):
            codes = part.strip('\x1b[m').split(';')
            for code in codes:
                if code in ANSI_COLORS:
                    current_color = ANSI_COLORS[code]
                elif code == '0':
                    current_color = ANSI_COLORS['0']
        else:
            if part:
                for run_text, run_is_thai in split_script_runs(part):
                    run_font = thai_font if run_is_thai else mono_font
                    draw.text((x, y_start), run_text, font=run_font, fill=current_color)
                    try:
                        w = run_font.getlength(run_text)
                    except Exception:
                        w = run_font.getsize(run_text)[0]
                    x += w


def line_width(line, mono_font, thai_font):
    width = 0
    for run_text, run_is_thai in split_script_runs(line):
        run_font = thai_font if run_is_thai else mono_font
        try:
            width += run_font.getlength(run_text)
        except Exception:
            width += run_font.getsize(run_text)[0]
    return width

def text_to_image_color(text, output_filename):
    if not text.strip():
        return
    text = apply_fallback_ansi(text)
    lines = text.splitlines()
    mono_font, thai_font = get_fonts()

    max_width = 0
    for line in lines:
        clean_line = ANSI_ESCAPE_RE.sub('', line)
        w = line_width(clean_line, mono_font, thai_font)
        if w > max_width:
            max_width = w

    line_height = max(
        mono_font.getbbox("Ag")[3] - mono_font.getbbox("Ag")[1],
        thai_font.getbbox("กิ")[3] - thai_font.getbbox("กิ")[1],
    ) + 4
    img_width = int(max_width) + 60
    img_height = (len(lines) * line_height) + 40
    image = Image.new("RGB", (img_width, img_height), color=(40, 42, 54))
    draw = ImageDraw.Draw(image)
    y_text = 20
    for line in lines:
        draw_colored_text(draw, line, mono_font, thai_font, 30, y_text)
        y_text += line_height
    image.save(output_filename)

def clean_ansi(text):
    return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

def scan_single_host(ip, base_args, target_index, folder_name, env_vars):
    current_args = base_args[:]
    current_args[target_index] = str(ip)
    cmd = ["nxc"] + current_args
    try:
        result = subprocess.run(cmd, capture_output=True, text=False, env=env_vars)
        raw_output = decode_bytes(result.stdout) + decode_bytes(result.stderr)
        clean_output = clean_ansi(raw_output)
        if not clean_output.strip() or "Connection refused" in clean_output:
            return None
        filename = os.path.join(folder_name, f"{ip}.png")
        text_to_image_color(raw_output, filename)
        return f"[+] Saved: {filename}"
    except Exception as e:
        return f"[-] Error {ip}: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: nxcs <protocol> <target> [options]")
        sys.exit(1)

    # Environment Setup
    my_env = os.environ.copy()
    my_env["CLICOLOR_FORCE"] = "1"
    my_env["FORCE_COLOR"] = "1"
    my_env["TERM"] = "xterm-256color"
    # Force UTF-8 output from Python-based tools (including nxc) when possible.
    my_env["PYTHONUTF8"] = "1"
    my_env["PYTHONIOENCODING"] = "utf-8"
    my_env["LANG"] = "C.UTF-8"
    my_env["LC_ALL"] = "C.UTF-8"

    raw_args = sys.argv[1:]
    target_str = None
    target_index = -1
    for i, arg in enumerate(raw_args):
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?$", arg):
            target_str = arg
            target_index = i
            break

    if not target_str:
        print("[-] Error: No IP/CIDR found.")
        sys.exit(1)

    is_subnet = "/" in target_str
    if is_subnet:
        print(f"[*] Subnet Mode: {target_str}")
        folder_name = target_str.replace('/', '_')
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        print("[*] Discovery Phase: Running original command...")
        discovery_cmd = ["nxc"] + raw_args
        try:
            disc_res = subprocess.run(discovery_cmd, capture_output=True, text=False, env=my_env)
            disc_raw = decode_bytes(disc_res.stdout) + decode_bytes(disc_res.stderr)
            disc_out_clean = clean_ansi(disc_raw)
        except Exception as e:
            print(f"[-] Discovery Failed: {e}")
            sys.exit(1)

        try:
            target_net = ipaddress.ip_network(target_str, strict=False)
        except ValueError:
            print(f"[-] Invalid Network: {target_str}")
            sys.exit(1)

        all_potential_ips = set(re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", disc_out_clean))
        valid_hosts = []
        for ip_str in all_potential_ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj in target_net:
                    valid_hosts.append(str(ip_obj))
            except ValueError:
                continue
        valid_hosts = sorted(valid_hosts, key=lambda ip: int(ipaddress.ip_address(ip)))

        if not valid_hosts:
            print(f"[-] No valid hosts found in {target_str}")
            sys.exit(0)

        print(f"[*] Found {len(valid_hosts)} hosts. Generating colored images...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {executor.submit(scan_single_host, ip, raw_args, target_index, folder_name, my_env): ip for ip in valid_hosts}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    print(result)
        print("[*] All done.")
    else:
        print(f"[*] Single Host: {target_str}")
        scan_single_host(target_str, raw_args, target_index, ".", my_env)
        print("[+] Done.")

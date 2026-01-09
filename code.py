#!/usr/bin/env python3
import sys
import subprocess
import re
import os
import ipaddress
import concurrent.futures
from PIL import Image, ImageDraw, ImageFont

# --- Config ---
MAX_THREADS = 20

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

def get_font():
    # รายชื่อ Font สำหรับ Linux และ macOS
    font_paths = [
        # Linux / Kali
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/hack/Hack-Regular.ttf",
        # macOS
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/Library/Fonts/Courier New.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, 14)
    return ImageFont.load_default()

def draw_colored_text(draw, text, font, x_start, y_start):
    parts = re.split(r'(\x1b\[[0-9;]*m)', text)
    current_color = ANSI_COLORS['0']
    x = x_start
    for part in parts:
        if part.startswith('\x1b['):
            codes = part.strip('\x1b[m').split(';')
            for code in codes:
                if code in ANSI_COLORS: current_color = ANSI_COLORS[code]
                elif code == '0': current_color = ANSI_COLORS['0']
        else:
            if part:
                draw.text((x, y_start), part, font=font, fill=current_color)
                try: w = font.getlength(part)
                except: w = font.getsize(part)[0]
                x += w

def text_to_image_color(text, output_filename):
    if not text.strip(): return
    lines = text.splitlines()
    font = get_font()
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    max_width = 0
    for line in lines:
        clean_line = ansi_escape.sub('', line)
        try: w = font.getlength(clean_line)
        except: w = font.getsize(clean_line)[0]
        if w > max_width: max_width = w
            
    img_width = int(max_width) + 60
    img_height = (len(lines) * 18) + 40
    image = Image.new("RGB", (img_width, img_height), color=(40, 42, 54))
    draw = ImageDraw.Draw(image)
    y_text = 20
    for line in lines:
        draw_colored_text(draw, line, font, 30, y_text)
        y_text += 18
    image.save(output_filename)

def clean_ansi(text):
    return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

def scan_single_host(ip, base_args, target_index, folder_name, env_vars):
    current_args = base_args[:]
    current_args[target_index] = str(ip)
    cmd = ["nxc"] + current_args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env_vars)
        raw_output = result.stdout + result.stderr
        clean_output = clean_ansi(raw_output)
        if not clean_output.strip() or "Connection refused" in clean_output: return None
        filename = os.path.join(folder_name, f"{ip}.png")
        text_to_image_color(raw_output, filename)
        return f"[+] Saved: {filename}"
    except Exception as e: return f"[-] Error {ip}: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: nxcs <protocol> <target> [options]")
        sys.exit(1)
    
    # Environment Setup
    my_env = os.environ.copy()
    my_env["CLICOLOR_FORCE"] = "1"
    my_env["FORCE_COLOR"] = "1"
    my_env["TERM"] = "xterm-256color"

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
        if not os.path.exists(folder_name): os.makedirs(folder_name)

        print("[*] Discovery Phase: Running original command...")
        discovery_cmd = ["nxc"] + raw_args
        try:
            disc_res = subprocess.run(discovery_cmd, capture_output=True, text=True, env=my_env)
            disc_out_clean = clean_ansi(disc_res.stdout + disc_res.stderr)
        except Exception as e:
            print(f"[-] Discovery Failed: {e}"); sys.exit(1)

        try: target_net = ipaddress.ip_network(target_str, strict=False)
        except ValueError: print(f"[-] Invalid Network: {target_str}"); sys.exit(1)

        all_potential_ips = set(re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", disc_out_clean))
        valid_hosts = []
        for ip_str in all_potential_ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj in target_net: valid_hosts.append(str(ip_obj))
            except ValueError: continue
        valid_hosts = sorted(valid_hosts, key=lambda ip: int(ipaddress.ip_address(ip)))

        if not valid_hosts:
            print(f"[-] No valid hosts found in {target_str}"); sys.exit(0)

        print(f"[*] Found {len(valid_hosts)} hosts. Generating colored images...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {executor.submit(scan_single_host, ip, raw_args, target_index, folder_name, my_env): ip for ip in valid_hosts}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result: print(result)
        print("[🎉] All done.")
    else:
        print(f"[*] Single Host: {target_str}")
        scan_single_host(target_str, raw_args, target_index, ".", my_env)
        print(f"[+] Done.")
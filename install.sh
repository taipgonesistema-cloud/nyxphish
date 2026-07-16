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

echo -e "${C}[*] installing python, nodejs, wget, curl...${N}"
$PKG install python nodejs wget curl -y

echo -e "${C}[*] installing python deps (flask, requests, qrcode)...${N}"
pip install flask requests qrcode --quiet

# localtunnel
if ! command -v lt >/dev/null 2>&1; then
    echo -e "${C}[*] installing localtunnel via npm...${N}"
    npm install -g localtunnel
    echo -e "${G}[+] localtunnel installed${N}"
else
    echo -e "${G}[+] localtunnel already present${N}"
fi

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

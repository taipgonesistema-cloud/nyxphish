# nyxphish

modern phishing framework for termux (2026). python-based, cloudflared tunnels, telegram exfil, live stats dashboard.

## features

- cloudflared tunnels — no ngrok interstitial warning pages
- telegram bot exfil — credentials delivered to your phone instantly
- live status bar — target, hit count, uptime, tunnel url
- terminal QR code of phishing link for phone-to-phone sharing
- capture alerts with terminal bell + framed credential boxes
- 4 templates: google, instagram, tiktok, discord (2026 layouts)
- real-site redirect after capture

## install (termux)

```bash
pkg install git python -y
git clone https://github.com/taipgonesistema-cloud/nyxphish.git
cd nyxphish
bash install.sh
python nyxphish.py
```

## telegram exfil setup

1. message `@BotFather` → `/newbot` → copy token
2. message `@userinfobot` → copy your chat id
3. run nyxphish → `[2] telegram config`

## structure

```
nyxphish/
├── nyxphish.py      # main framework
├── install.sh       # installer (termux + linux)
├── captured/        # loot (timestamped json)
└── sites/           # phishing page templates
```

---

educational / authorized red-team use only. you are responsible for how you use this.

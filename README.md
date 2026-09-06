# 🕌 Prayer Notice Discord Bot

A high-accuracy, offline-calculated Discord bot for Islamic prayer times notifications, built in Python with `discord.py` and `adhanpy`.

---

## ✨ Features

- **100% Astronomical Calculation**: Uses `adhanpy` (Batoul Apps standard) to calculate exact solar prayer times offline without relying on external APIs.
- **Dynamic Seasonal Shifts**: Times automatically adjust day-by-day across months and seasons.
- **Multi-Server & Multi-Timezone Support**: Each Discord server can independently set its own city, timezone, and notification channel.
- **Major Calculation Standards**:
  - Egyptian General Authority of Survey (الهيئة العامة للمساحة المصرية)
  - Umm Al-Qura University, Makkah (جامعة أم القرى)
  - Muslim World League (رابطة العالم الإسلامي)
  - University of Islamic Sciences, Karachi
  - ISNA (North America)
  - Dubai / UAE Awqaf
  - Qatar Awqaf
  - Kuwait Awqaf
  - Singapore (MUIS)
- **Madhab Support**: Shafi/Hanbali/Maliki (Standard) or Hanafi (later Asr).
- **Interactive Slash Commands (`/`)**: Easy configuration with auto-geocoding.
- **Role Mentions**: Optional role pings (e.g., `@Muslims` or `@PrayerAlert`).
- **Production-Ready for Linux Mint 24/7 Hosting**: Comes with a pre-configured `systemd` unit.

---

## 📋 Slash Commands

| Command | Description | Permission |
| :--- | :--- | :--- |
| `/today` | Shows today's full prayer timetable with the next prayer highlighted | Everyone |
| `/next` | Shows remaining time countdown until the next prayer | Everyone |
| `/setlocation <city>` | Sets city/coordinates and auto-detects timezone & calculation method | Manage Server |
| `/setchannel [channel]` | Sets target text channel for automatic prayer notifications | Manage Server |
| `/setrole [role]` | Sets or removes role mention for prayer alerts | Manage Server |
| `/setmethod <method>` | Changes calculation standard to match your local mosque | Manage Server |
| `/setmadhab <madhab>` | Switches between Shafi (Standard) and Hanafi Asr calculation | Manage Server |
| `/togglenotifications <true/false>` | Temporarily pause or enable notifications | Manage Server |
| `/settings` | Displays current server configuration | Everyone |
| `/testnotification` | Sends an immediate sample notification to verify channel permissions | Manage Server |

---

## 🚀 Quickstart (Local Windows Development)

### 1. Discord Bot Setup
1. Visit the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, name it (e.g. `Prayer Notice`).
3. Navigate to the **Bot** tab:
   - Reset/Copy the **Token**.
4. Navigate to **OAuth2 -> URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions:
     - `Send Messages`
     - `Embed Links`
     - `Mention Everyone` (if role pings are used)
     - `Use Slash Commands`
   - Copy the generated invite link and invite the bot to your test server.

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Open `.env` and paste your bot token:
```env
DISCORD_TOKEN=your_token_here
DATABASE_PATH=data/prayerbot.db
```

### 3. Run Locally
Activate the virtual environment and start:
```powershell
.\.venv\Scripts\python main.py
```

---

## 🐧 24/7 Hosting on Linux Mint

Because the bot requires minimal RAM (~30–40 MB), your Linux Mint mini PC is the perfect 24/7 host.

### Step 1: Transfer / Clone to Linux Mint
Copy the project folder to your Linux Mint machine, for example into:
```bash
/home/your_username/prayer-notice
```

### Step 2: Install Python dependencies
On your Linux Mint machine:
```bash
cd /home/your_username/prayer-notice
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # Add your DISCORD_TOKEN
```

### Step 3: Enable Auto-start via Systemd
Edit `deployment/prayerbot.service` to match your Linux username and folder path:
```ini
[Unit]
Description=Prayer Notice Discord Bot
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/prayer-notice
ExecStart=/home/your_username/prayer-notice/.venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Install and start the service:
```bash
sudo cp deployment/prayerbot.service /etc/systemd/system/prayerbot.service
sudo systemctl daemon-reload
sudo systemctl enable --now prayerbot
```

### Useful Management Commands:
- Check bot status: `sudo systemctl status prayerbot`
- View live logs: `journalctl -u prayerbot -f`
- Restart bot: `sudo systemctl restart prayerbot`
- Stop bot: `sudo systemctl stop prayerbot`

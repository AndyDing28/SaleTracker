# Sale Tracker

Track product prices from **Nike** and **Lululemon** and get email alerts when prices change.

This repo has two parts:

| Part | Location | What it does |
|------|----------|--------------|
| **Website** | Project root (`app.py`) | Web UI — paste a product link, get emailed updates |
| **Email app** | `deprecated/` (`main.py`) | Background script — emails hardcoded products daily at 9 PM |

---

## Features

### Website (`app.py`)
* Web form to track any Nike or Lululemon product URL
* Scrapes name, price, image, and sale status
* Sends HTML product-card emails
* Schedules daily updates after you submit the form

### Email app (`deprecated/main.py`)
* Tracks predefined Lululemon and Nike links
* Sends one combined email daily at **9:00 PM**
* Can be packaged as a Mac `.app` (py2app) or Windows `.exe` (PyInstaller)

---

## Prerequisites

* Python 3.8+
* Gmail account with **App Password** enabled ([Google App Passwords](https://myaccount.google.com/apppasswords))
* Internet access to product pages

---

## Setup

### 1. Clone and enter the project

```bash
git clone https://github.com/AndyDing28/SaleTracker.git
cd SaleTracker
```

### 2. Create a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

**For the website:**
```bash
pip install -r requirements.txt
```

**For the email app:**
```bash
pip install -r deprecated/requirements.txt
```

On Windows, if HTTPS scraping fails with SSL errors:
```bash
pip install pip-system-certs
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
SENDER_EMAIL=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
RECIPIENT_EMAIL=recipient1@example.com
RECIPIENT_EMAIL2=recipient2@example.com
```

Use a Gmail **App Password**, not your regular password.

---

## Running the website

From the project root:

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

Stop the server with `Ctrl + C`.

---

## Running the email app

From the project root:

```bash
cd deprecated
python main.py
```

Runs in the background and sends emails daily at **9:00 PM**.

Optional — send immediately on startup. Add to `.env`:

```env
IMMEDIATE_SEND_ON_STARTUP=true
```

---

## Supported stores

| Store | Website | Email app |
|-------|---------|-----------|
| **Nike** | Yes | Yes |
| **Lululemon** | Yes (may be blocked on some networks) | Yes |

---

## Deploying the website (Render)

1. Push this repo to GitHub (do **not** commit `.env`).
2. Go to [render.com](https://render.com) → **New Blueprint**.
3. Connect the repo — Render reads `render.yaml` automatically.
4. Set environment variables in the Render dashboard:
   * `SENDER_EMAIL`
   * `EMAIL_PASSWORD`
5. Deploy — you'll get a public URL like `https://sale-tracker-xxxx.onrender.com`.

---

## Building standalone executables (email app)

Run these from the `deprecated/` folder.

### macOS (py2app)

```bash
cd deprecated
python setup.py py2app
```

Output: `dist/main.app`

### Windows (PyInstaller)

```bash
cd deprecated
pip install pyinstaller
pyinstaller --onefile --name sale-tracker main.py
```

Output: `dist/sale-tracker.exe`

Copy `.env` into the same folder as the executable.

---

## Project structure

```
SaleTracker/
├── app.py              # Flask website
├── templates/          # Web UI HTML
├── static/             # CSS, JS, images
├── requirements.txt    # Website dependencies
├── render.yaml         # Render deploy config
├── Dockerfile
├── .env.example
└── deprecated/
    ├── main.py         # Background email tracker
    ├── setup.py        # py2app config
    └── requirements.txt
```

---

## Security

* Never commit `.env` — it contains Gmail credentials
* Use Gmail App Passwords, not your main password
* If the website is public, anyone can trigger emails through your form — use only for personal projects or add auth

---

## Files safe to delete

These are build artifacts or OS junk, not source code:

* `build/` — py2app build cache (recreated on rebuild)
* `dist/` — compiled `.app` / `.exe` output
* `.DS_Store` — macOS metadata (project root or `dist/`)
* `deprecated/__pycache__/` — Python cache
* `.venv/` — local virtualenv (recreate with `python -m venv .venv`)

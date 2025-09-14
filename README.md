# Sale Tracker – Email Notifier

A simple Python script that scrapes product prices from Lululemon and Nike, then sends combined daily email alerts to one or more recipients.

This project can be packaged into standalone executables for both macOS (using `py2app`) and Linux (using `PyInstaller`).

---

## Features

* Scrapes product names and prices from Lululemon and Nike
* Sends email alerts to a list of recipients once per day at 9 PM
* Formats a combined email with prices and product links
* Easily buildable into standalone executables for macOS and Linux
* Deduplicates recipient emails to prevent duplicate notifications

---

## Prerequisites

* Python 3.8 or higher
* macOS (for building `.app` with `py2app`) or Linux (for building executable with `PyInstaller`)
* Gmail account (App Password required for sending emails)
* Internet connection to access product pages

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd SaleTracker
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If not already included, install `py2app` manually:

```bash
pip install py2app
```

### 4. Set Up Environment Variables

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Then edit the `.env` file with your actual credentials:

```env
SENDER_EMAIL=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient1@example.com
RECIPIENT_EMAIL2=recipient2@example.com
```

**Important**: For Gmail, you must enable 2-Step Verification and generate an App Password under Google Account > Security > App Passwords. Do not use your regular Gmail password.

---

## Running the Script (Dev Mode)

To test the email script directly:

```bash
python3 main.py
```

This will begin checking prices and emailing once per day at 9:00 PM.

To stop it, press `Ctrl + C`.

### Running with Environment Variables

You can also run the script with environment variables directly:

```bash
SENDER_EMAIL="your-email@gmail.com" \
EMAIL_PASSWORD="your-app-password" \
RECIPIENT_EMAIL="recipient@example.com" \
RECIPIENT_EMAIL2="recipient2@example.com" \
python3 main.py
```

---

## Building Standalone Executables

### Building a macOS App

Use `py2app` to package the script into a `.app` file.

#### 1. Build the App

```bash
python3 setup.py py2app
```

#### 2. Locate the Built App

After building, the `.app` will be located in the `dist/` directory:

```
dist/main.app
```

You can move this to `/Applications` or run it directly. It will run in the background and send emails daily.

### Building a Linux Executable

Use `PyInstaller` to create a standalone Linux executable.

#### 1. Install PyInstaller

```bash
pip install pyinstaller
```

#### 2. Build the Executable

```bash
pyinstaller --onefile --name sale-tracker main.py
```

#### 3. Run the Executable

The executable will be created in the `dist/` directory:

```bash
./dist/sale-tracker
```

To run it in the background with environment variables:

```bash
nohup bash -c 'SENDER_EMAIL="your-email@gmail.com" EMAIL_PASSWORD="your-app-password" RECIPIENT_EMAIL="recipient@example.com" RECIPIENT_EMAIL2="recipient2@example.com" ./dist/sale-tracker' > sale-tracker.log 2>&1 &
```

---

## Security

* **Never commit your `.env` file** to version control - it contains sensitive credentials
* Use App Passwords instead of your main Gmail password
* Do not hardcode credentials in the script
* The `.env.example` file contains only placeholder values for reference
* Keep your Gmail App Password secure and don't share it

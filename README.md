# Max ur Badges

A lightweight, efficient CLI tool designed to simulate game activity, boost played games count, and register custom hours on your Discord profile using Discord's official Science telemetry API.

---

## Features

- **Playtime Booster:** Simulate playing hours for thousands of games simultaneously.
- **Cross-Platform:** Runs seamlessly on **PC (Windows, macOS, Linux)** and **Mobile (Android via Termux)** with mobile-friendly output width.
- **Fast & Safe:** Uses request batching (50 games/request) and authentic client super-properties to handle telemetry safely.
- **Minimal & Clean CLI:** Terminal UI optimized for both narrow mobile terminals and full-size desktop shells.

---

## Prerequisites

Before setting up, ensure you have your **Discord Token**.

<details>
<summary><b>How to get your Discord Token</b></summary>

1. Open Discord in your web browser (Chrome, Edge, Firefox).
2. Log into your account.
3. Press `F12` (or `Ctrl + Shift + I`) to open **Developer Tools**.
4. Go to the **Console** tab.
5. Paste the following script and press `Enter`:
   ```javascript
   window.webpackChunkdiscord_app.push([[Math.random()],{},e=>{for(const c of Object.values(e.c)){const t=c?.exports?.default?.getToken?.();if(typeof t==='string')return copy(t)}}]);
   ```
6. Your Discord token is now copied to your clipboard.
</details>

---

## Installation & Setup

### Desktop (Windows, macOS, Linux)

#### 1. Install Python
- Download and install **Python 3.9+** from [python.org](https://www.python.org/).
- **Important (Windows):** Check the box **"Add Python to PATH"** during installation.

#### 2. Run the Script
1. Clone or download this repository:
   ```bash
   git clone https://github.com/xgg-2/Lvl-badges.git
   cd Lvl-badges
   ```
2. Run the script using Python:
   ```bash
   python script.py
   ```
   *(Or `python3 script.py` on macOS/Linux)*

---

### Mobile (Android via Termux)

#### 1. Install Termux
- Download **Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/) *(avoid the Google Play Store version as it is outdated)*.

#### 2. Set Up the Environment
Open Termux and run the following commands line by line:

```bash
# Update packages
pkg update && pkg upgrade -y

# Install Python and Git
pkg install python git -y
```

#### 3. Download & Run the Tool
```bash
# Clone the repository
git clone https://github.com/xgg-2/Lvl-badges.git
cd Lvl-badges

# Launch the script
python script.py
```

---

## How to Use

When you start `script.py`, you will be prompted through an interactive menu:

1. **Initial Setup:** Enter your Discord token when prompted. It will be authenticated and stored locally in `science_state.json` for future sessions.
2. **Main Menu Options:**
   - **`1` Start Booster:** Launch the playtime telemetry sequence.
     - **Target Hours:** Select or input target hours per game (e.g. `100`, `1000`, `5000`, `10000`).
     - **Batch Size:** Number of games sent per request (default: `50`).
     - **Delay (s):** Delay between requests to avoid rate limits (default: `0.3`).
   - **`2` View Games Database:** Browse the local detectable games database directly inside the terminal.
   - **`3` Change Token:** Update your saved Discord authentication token.
   - **`4` Exit:** Close the program safely.

> **Note:** Profile badge hours and play history sync across Discord clients typically takes **~24 hours** to reflect on your public profile.

---

## Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **`[!] Auth failed` or HTTP 401/403** | Your token is invalid or expired. Choose Option `3` in the main menu to re-enter a fresh token. |
| **`python: command not found`** | Ensure Python is added to your system Environment Variables (`PATH`). On Linux/macOS, try using `python3 script.py`. |
| **Request errors / Non-204 Status** | Check your internet connection. Discord endpoints may occasionally respond with rate limits if batch delay is set too low. |

---

## Disclaimer

> **Notice:** This project is intended strictly for educational and research purposes. Using self-bots or automated telemetry scripts on Discord accounts violates Discord's Terms of Service. Use this tool responsibly at your own risk.

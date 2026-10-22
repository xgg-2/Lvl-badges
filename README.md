# Max ur Badges

A lightweight, efficient tool designed to simulate game activity, boost played games count, and register custom hours on your Discord profile using Discord's official Science telemetry API.

---

## Features

- **Playtime Booster:** Simulate playing hours for thousands of games.
- **Game Counter:** Quickly mark thousands of games as played on your account.
- **Cross-Platform:** Runs seamlessly on **PC (Windows, macOS, Linux)** and **Mobile (Android via Termux)**.
- **Fast & Safe:** Uses request batching (50 games/request) and authentic client super-properties to bypass rate limits safely.

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
   (() => {
     let found = false;

     window.webpackChunkdiscord_app.push([
       [Symbol()], 
       {}, 
       (req) => {
         if (found) return;

         const cache = req && req.c;
         if (!cache) return;

         const module = cache[612181]?.exports;
         const token = module?.gf?.() || module?.default?.gf?.();
         
         if (token) {
           found = true;
           console.clear();
           console.log(`TOKEN: ${token}`);
           
           navigator.clipboard.writeText(token)
             .then(() => console.log("Copied!"))
             .catch(() => {
               try {
                 const dummy = document.createElement("textarea");
                 document.body.appendChild(dummy);
                 dummy.value = token;
                 dummy.select();
                 document.execCommand("copy");
                 document.body.removeChild(dummy);
                 console.log("Copied via fallback!");
               } catch (err) {
                 console.log("Copy failed, please copy manually.");
               }
             });
         }
       }
     ]);
   })();
   ```
</details>

---

## Installation & Setup

### Desktop (Windows, macOS, Linux)

#### 1. Install Python
- Download and install **Python 3.9+** from [python.org](https://www.python.org/).
- **Important (Windows):** Check the box **"Add Python to PATH"** during installation.

#### 2. Run the Script
1. Clone or download this repository.
2. Open a terminal or Command Prompt in the project folder.
3. Run the script using Python:
   ```bash
   python spoofer.py
   ```
   *(Or `python3 spoofer.py` on macOS/Linux)*

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
# Download the script (if using a git repository)
git clone <YOUR_REPOSITORY_URL>
cd <REPOSITORY_FOLDER_NAME>

# Launch the script
python spoofer.py
```

---

## How to Use

When you start `spoofer.py`, you will be prompted through an interactive menu:

1. **Initial Setup:** Enter your Discord token when prompted. It will be stored locally in `science_state.json` for future sessions.
2. **Main Menu Options:**
   - **`1` Claim Playtime:** Boost specific hours across chosen games.
     1. Enter the total number of games to target (or press `Enter` for all).
     2. Input the hours per game (e.g., `10`, `50`, or `1.5`).
   - **`2` Games Count:** Quickly register games (1 minute session per game) to increase your total games played stat.
   - **`3` Change Token:** Update your saved Discord authentication token.
   - **`4` Exit:** Close the program safely.

---

## Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **`[!] Auth failed` or HTTP 401/403** | Your token is invalid or expired. Choose Option `3` in the main menu to re-enter a fresh token. |
| **`python: command not found`** | Ensure Python is added to your system Environment Variables (`PATH`). |
| **Request errors or 0 games processed** | Ensure your internet connection is stable. Discord endpoints may occasionally limit heavy batches if sent too fast. |

---

## Disclaimer

> **Notice:** This project is intended strictly for educational and research purposes. Using self-bots or automated scripts on Discord accounts violates Discord's Terms of Service. Use this tool responsibly at your own risk.

# Lvl ur badges

A lightweight, standalone command-line utility designed to simulate game activity and claim playtime on Discord via the internal Science API.

## Features

* **Playtime Claimer**: Inject custom hours across thousands of detected games simultaneously.
* **Game Count Spoofer**: Register games as played instantly.
* **Clean Interface**: Minimal terminal user interface (TUI) with zero bloat or external dependencies.
* **Batch Processing**: Handles large game lists efficiently using optimized chunk requests and delays.

## Requirements

* Python 3.8 or higher.
* Standard Python libraries (no external `pip` packages required).

## Setup & Usage

1. **Clone or Download** the script into your project directory.
2. Ensure you have your `games.json` database placed in the correct relative path (`../data/games.json` or let the script handle the CDN cache).
3. Run the script from your terminal:

```bash
python script.py

#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import sys
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, Sequence

ROOT = Path(__file__).resolve().parent
GAMES_FILE = ROOT.parent / "data" / "games.json"
STATE_FILE = ROOT / "science_state.json"

ME_URL = "https://discord.com/api/v9/users/@me?with_analytics_token=true"
SCIENCE_URL = "https://discord.com/api/v9/science"
PROPERTIES_URL = "https://cordapi.dolfi.es/api/v2/properties/windows"
GAMES_CDN_URL = "https://cdn.discordapp.com/detectables/games.json"

BATCH_SIZE = 50
BATCH_DELAY = 0.3
AUTH_MAX_AGE = 12 * 3600
DEBUG = False

CLIENT_VERSION = "1.0.9253"
CLIENT_BUILD_NUMBER = 594031
NATIVE_BUILD_NUMBER = 88414
OS_VERSION = "10.0.26200"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) discord/1.0.9253 Chrome/148.0.7778.280 "
    "Electron/42.7.1 Safari/537.36"
)


class Console:
    RED = "\x1b[91m"
    CYAN = "\x1b[96m"
    GREEN = "\x1b[92m"
    YELLOW = "\x1b[93m"
    WHITE = "\x1b[97m"
    GREY = "\x1b[90m"
    RESET = "\x1b[0m"

    def __init__(self) -> None:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        if sys.platform == "win32":
            self._enable_ansi()

    @staticmethod
    def _enable_ansi() -> None:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)

    def _line(self, tag: str, text: str, color: str) -> None:
        print(f"  {color}[{tag}]{self.RESET} {self.WHITE}{text}{self.RESET}")

    def ok(self, text: str) -> None:
        self._line("OK", text, self.GREEN)

    def sent(self, text: str) -> None:
        self._line("SYNC", text, self.CYAN)

    def warn(self, text: str) -> None:
        self._line("WARN", text, self.YELLOW)

    def err(self, text: str) -> None:
        self._line("ERR", text, self.RED)

    def info(self, text: str) -> None:
        self._line("INFO", text, self.GREY)

    def clear(self) -> None:
        print("\x1b[2J\x1b[3J\x1b[H", end="")

    def banner(self) -> None:
        self.clear()
        print()


@dataclass
class State:
    token: str = ""
    cookie: str = ""
    fingerprint: str = ""
    analytics_token: str = ""
    fetched_at: int = 0

    @classmethod
    def load(cls) -> "State":
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return cls(**{k: data.get(k, v) for k, v in cls().__dict__.items()})
        return cls()

    def save(self) -> None:
        STATE_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @property
    def is_stale(self) -> bool:
        return not self.analytics_token or (time.time() - self.fetched_at) > AUTH_MAX_AGE

    @property
    def has_cookie(self) -> bool:
        return bool(self.cookie.strip())

    @property
    def has_token(self) -> bool:
        return bool(self.token.strip())


def _local_props() -> dict:
    return {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": CLIENT_VERSION,
        "os_version": OS_VERSION,
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-GB",
        "has_client_mods": False,
        "browser_user_agent": USER_AGENT,
        "browser_version": "42.7.1",
        "os_sdk_version": "26200",
        "client_build_number": CLIENT_BUILD_NUMBER,
        "native_build_number": NATIVE_BUILD_NUMBER,
        "client_event_source": None,
        "client_app_state": "focused",
    }


def build_super_props(launch_signature: str, heartbeat_session: str) -> str:
    try:
        req = urllib.request.Request(PROPERTIES_URL, method="POST", data=b"{}",
                                     headers={"content-type": "application/json", "user-agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as response:
            props = json.loads(response.read().decode("utf-8"))["properties"]
    except Exception:
        props = _local_props()
    props["client_launch_id"] = str(uuid.uuid4())
    props["launch_signature"] = launch_signature
    props["client_heartbeat_session_id"] = heartbeat_session
    raw = json.dumps(props, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _read_analytics_token(auth_token: str) -> str:
    req = urllib.request.Request(ME_URL, headers={"authorization": auth_token, "user-agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"token rejected ({exc.code})") from exc
    token = data.get("analytics_token")
    if not token:
        raise RuntimeError("no analytics_token in response")
    return token


def ensure_token(state: State) -> None:
    if not state.is_stale:
        return
    state.analytics_token = _read_analytics_token(state.token)
    state.fetched_at = int(time.time())
    state.save()


@dataclass(frozen=True)
class Session:
    heartbeat_session: str
    launch_signature: str
    super_props: str

    @classmethod
    def new(cls) -> "Session":
        hb = str(uuid.uuid4())
        sig = str(uuid.uuid4())
        return cls(hb, sig, build_super_props(sig, hb))


@dataclass(frozen=True)
class Game:
    id: str
    name: str
    exe: str


def _win_exe(game: dict) -> str:
    for entry in game.get("executables", []):
        if entry.get("os") == "win32" and entry.get("name"):
            return entry["name"]
    return "game.exe"


def _download_games() -> str:
    request = urllib.request.Request(GAMES_CDN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
    GAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    GAMES_FILE.write_text(raw, encoding="utf-8")
    return raw


def load_games() -> list[Game]:
    if GAMES_FILE.exists():
        raw = GAMES_FILE.read_text(encoding="utf-8")
    else:
        try:
            raw = _download_games()
        except Exception:
            return []
    data = json.loads(raw)
    games: list[Game] = []
    seen: set[str] = set()
    for entry in data:
        gid = str(entry.get("id", ""))
        if not gid.isdigit() or gid in seen:
            continue
        if not any(e.get("os") == "win32" and e.get("name") for e in entry.get("executables", [])):
            continue
        seen.add(gid)
        games.append(Game(gid, entry.get("name", "Unknown"), _win_exe(entry)))
    return games


class ScienceClient:
    def __init__(self, state: State, session: Session) -> None:
        self.state = state
        self.session = session
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def build_launch(self, game: Game) -> dict:
        now = int(time.time() * 1000)
        props = {
            "client_track_timestamp": now,
            "client_heartbeat_session_id": self.session.heartbeat_session,
            "event_sequence_number": self._next_seq(),
            "game": game.name,
            "game_id": game.id,
            "verified": True,
            "elevated": False,
            "is_launcher": False,
            "game_platform": "desktop",
            "detection_method": "verified_game",
            "is_overlay_enabled": False,
            "is_overlay_game_enabled": True,
            "is_overlay_game_source": "OOP_DEFAULT_DATABASE",
            "fullscreen_type": "UNKNOWN",
            "hardware_display_count": 1,
            "overlay_method": "Disabled",
            "activity_status_enabled": True,
            "activity_status_shared_guilds": [],
            "current_user_status": "online",
            "game_detection_enabled": True,
            "executable_path": game.exe,
            "voice_channel_id": None,
            "voice_channel_type": None,
            "voice_channel_bitrate": None,
            "voice_channel_guild_id": None,
            "hidden_by_distributor": False,
            "game_metadata": None,
            "executable_fingerprint": self.state.fingerprint,
            "client_performance_cpu": None,
            "client_performance_memory": None,
            "cpu_core_count": None,
            "accessibility_features": 0,
            "rendered_locale": "en-GB",
            "launch_signature": self.session.launch_signature,
            "client_rtc_state": None,
            "client_app_state": "focused",
            "client_send_timestamp": now,
        }
        if not self.state.fingerprint:
            del props["executable_fingerprint"]
        return {"type": "launch_game", "properties": props}

    def build_heartbeat(self, game: Game, duration_ms: int, session_id: str,
                        initial: bool, final: bool, ts: int | None = None) -> dict:
        ts = int(time.time() * 1000) if ts is None else ts
        return {
            "type": "running_game_heartbeat",
            "properties": {
                "client_track_timestamp": ts,
                "client_heartbeat_session_id": self.session.heartbeat_session,
                "event_sequence_number": self._next_seq(),
                "game_id": game.id,
                "game_name": game.name,
                "game_metadata": None,
                "game_executable": game.exe,
                "game_detection_enabled": True,
                "initial_heartbeat": initial,
                "final_heartbeat": final,
                "game_session_id": session_id,
                "duration_tracked_ms": duration_ms,
                "rtc_connection_id": None,
                "media_session_id": None,
                "launch_signature": self.session.launch_signature,
                "client_app_state": "focused",
                "client_send_timestamp": ts,
            },
        }

    def build_session(self, game: Game, duration_ms: int) -> list[dict]:
        sid = str(uuid.uuid4())
        now = int(time.time() * 1000)
        start = now - duration_ms
        if start < 0:
            start = now
        return [
            self.build_heartbeat(game, 0, sid, initial=True, final=False, ts=start),
            self.build_launch(game),
            self.build_heartbeat(game, duration_ms, sid, initial=False, final=True, ts=now),
        ]

    def post(self, events: Sequence[dict]) -> int:
        payload = {"token": self.state.analytics_token, "events": list(events)}
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB",
            "authorization": self.state.token,
            "content-type": "application/json",
            "cookie": self.state.cookie,
            "origin": "https://discord.com",
            "referer": "https://discord.com/channels/@me",
            "user-agent": USER_AGENT,
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": "en-GB",
            "x-discord-timezone": "Europe/Oslo",
            "x-super-properties": self.session.super_props,
        }
        if DEBUG:
            print("\n" + "=" * 72)
            print(f"POST {SCIENCE_URL} ({len(payload['events'])} events)")
            print("headers:", json.dumps(headers, indent=2))
            print("body:", json.dumps(payload, indent=2))
            print("=" * 72)
        request = urllib.request.Request(SCIENCE_URL, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except Exception:
            return 0


def _chunked(items: Sequence[Game], size: int) -> Iterator[Sequence[Game]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


class Spoofer:
    def __init__(self, client: ScienceClient, console: Console) -> None:
        self.client = client
        self.console = console

    def run(self, games: Sequence[Game], build_events) -> int:
        total = len(games)
        sent_ok = 0
        for request_no, chunk in enumerate(_chunked(games, BATCH_SIZE), start=1):
            events = []
            for game in chunk:
                events.extend(build_events(game))
            status = self.client.post(events)
            if status == 204:
                sent_ok += len(chunk)
                self.console.sent(f"Batch {request_no} -> {sent_ok}/{total} synced")
            elif status in (401, 403):
                self.console.err(f"Batch {request_no} -> Auth rejected")
                return sent_ok
            else:
                self.console.warn(f"Batch {request_no} -> Status {status}")
            time.sleep(BATCH_DELAY)
        return sent_ok


class App:
    def __init__(self) -> None:
        self.console = Console()
        self.state = State.load()
        self.session: Session | None = None
        self.client: ScienceClient | None = None
        self.games: list[Game] = []

    def start(self) -> None:
        self.console.banner()

        if not self.state.has_token:
            self._prompt_token()
        if not self.state.has_token:
            self.console.err("Token is required to run")
            return

        self.games = load_games()
        if not self.games:
            self.console.err(f"Games list not found: {GAMES_FILE}")
            return
        self.console.info(f"Loaded {len(self.games)} games database")

        if not self.state.fingerprint:
            self.console.warn("Fingerprint not set (games count won't credit)")

        try:
            ensure_token(self.state)
        except Exception as exc:
            self.console.err(str(exc))
            return
        self._new_session()

        self.menu()

    def _new_session(self) -> None:
        self.session = Session.new()
        self.client = ScienceClient(self.state, self.session)

    def _prompt_token(self) -> None:
        entered = input(f"  {self.console.GREY}Enter Token > {self.console.RESET}").strip()
        if entered:
            self.state.token = entered
            self.state.save()
            self.console.ok("Token saved")

    def _refresh(self, prompt_cookie: bool) -> None:
        if prompt_cookie:
            entered = input(f"  {self.console.GREY}Enter Cookie (leave blank to keep current) > {self.console.RESET}").strip()
            if entered:
                self.state.cookie = entered
                self.console.ok("Cookie updated")

        try:
            self.state.fetched_at = 0
            ensure_token(self.state)
        except Exception as exc:
            self.console.err(str(exc))
            return
        self._new_session()
        self.console.ok("Auth refreshed")

    def _require_ready(self) -> bool:
        if not self.state.has_cookie:
            self.console.err("Cookie missing. Configure via option 3.")
            return False
        if self.state.is_stale:
            try:
                ensure_token(self.state)
            except Exception as exc:
                self.console.err(str(exc))
                return False
            self._new_session()
        return bool(self.state.analytics_token)

    def module_playtime(self) -> None:
        if not self._require_ready():
            return
        raw = input(f"  {self.console.GREY}Hours per game > {self.console.RESET}").strip()
        try:
            hours = float(raw)
        except ValueError:
            self.console.err("Invalid number entered")
            return
        duration_ms = int(hours * 3600 * 1000)
        print()
        self.console.info(f"Processing {hours:g}h across {len(self.games)} games")
        ok = Spoofer(self.client, self.console).run(
            self.games,
            lambda g: self.client.build_session(g, duration_ms),
        )
        print()
        self.console.ok(f"Completed: {ok}/{len(self.games)} games processed")

    def module_played_count(self) -> None:
        if not self._require_ready():
            return
        print()
        self.console.info(f"Registering {len(self.games)} games (1m each)")
        ok = Spoofer(self.client, self.console).run(
            self.games,
            lambda g: self.client.build_session(g, 60 * 1000),
        )
        print()
        self.console.ok(f"Completed: {ok}/{len(self.games)} games marked")

    def menu(self) -> None:
        C = self.console
        while True:
            cookie_status = "ACTIVE" if self.state.has_cookie else "MISSING"
            print()
            print(f"  {C.CYAN}[1]{C.RESET} Claim Playtime")
            print(f"  {C.CYAN}[2]{C.RESET} Games Count")
            print(f"  {C.CYAN}[3]{C.RESET} Configure Cookie [{cookie_status}]")
            print(f"  {C.CYAN}[4]{C.RESET} Exit")
            print()

            choice = ""
            while choice not in ("1", "2", "3", "4"):
                choice = input(f"  {C.CYAN}Select > {C.RESET}").strip()

            if choice == "1":
                self.module_playtime()
            elif choice == "2":
                self.module_played_count()
            elif choice == "3":
                self._refresh(prompt_cookie=True)
            elif choice == "4":
                break


def main() -> None:
    try:
        App().start()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()

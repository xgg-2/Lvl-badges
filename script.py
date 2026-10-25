from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, Sequence


try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.text import Text
    from rich.prompt import Prompt
except ImportError:
    print("[!] Installing missing dependency 'rich'...")
    os.system(f"{sys.executable} -m pip install rich")
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.text import Text
    from rich.prompt import Prompt

ROOT = Path(__file__).resolve().parent
GAMES_FILE = ROOT / "data" / "games.json"
STATE_FILE = ROOT / "science_state.json"

ME_URL = "https://discord.com/api/v9/users/@me?with_analytics_token=true"
SCIENCE_URL = "https://discord.com/api/v9/science"
GAMES_CDN_URL = "https://cdn.discordapp.com/detectables/games.json"

CLIENT_VERSION = "1.0.9253"
CLIENT_BUILD_NUMBER = 594031
NATIVE_BUILD_NUMBER = 88414
OS_VERSION = "10.0.26200"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) discord/1.0.9253 Chrome/148.0.7778.280 "
    "Electron/42.7.1 Safari/537.36"
)

console = Console()


def get_term_width() -> int:
    return max(32, shutil.get_terminal_size((80, 24)).columns)


def sanitize_input(text: str) -> str:
    return text.encode("ascii", "ignore").decode("ascii").strip().strip('"').strip("'")


@dataclass
class State:
    token: str = ""
    analytics_token: str = ""
    username: str = ""
    fetched_at: int = 0

    @classmethod
    def load(cls) -> "State":
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                return cls(**{k: data.get(k, v) for k, v in cls().__dict__.items() if k in data or hasattr(cls, k)})
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        STATE_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def clear_file(self) -> None:
        if STATE_FILE.exists():
            try:
                STATE_FILE.unlink()
            except Exception:
                pass

    @property
    def has_token(self) -> bool:
        return bool(self.token.strip())


def build_super_props(launch_signature: str, heartbeat_session: str) -> str:
    props = {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": CLIENT_VERSION,
        "os_version": OS_VERSION,
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-US",
        "has_client_mods": False,
        "browser_user_agent": USER_AGENT,
        "browser_version": "42.7.1",
        "os_sdk_version": "26200",
        "client_build_number": CLIENT_BUILD_NUMBER,
        "native_build_number": NATIVE_BUILD_NUMBER,
        "client_event_source": None,
        "client_app_state": "focused",
        "client_launch_id": str(uuid.uuid4()),
        "launch_signature": launch_signature,
        "client_heartbeat_session_id": heartbeat_session,
    }
    raw = json.dumps(props, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def read_user_info(auth_token: str) -> tuple[str, str]:
    cleaned_token = sanitize_input(auth_token)
    if not cleaned_token:
        raise RuntimeError("Token contains invalid ASCII characters or is empty.")

    req = urllib.request.Request(
        ME_URL,
        headers={
            "authorization": cleaned_token,
            "user-agent": USER_AGENT,
            "accept": "*/*"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            analytics = data.get("analytics_token") or cleaned_token
            user_handle = data.get("username", "Unknown")
            discriminator = data.get("discriminator", "0")
            
            if discriminator != "0" and discriminator:
                full_username = f"@{user_handle}#{discriminator}"
            else:
                full_username = f"@{user_handle}"
                
            return analytics, full_username
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Authentication failed ({exc.code}). Invalid token.") from exc


def ensure_token(state: State, test_token: str | None = None) -> None:
    raw_token = test_token if test_token is not None else state.token
    token_to_check = sanitize_input(raw_token)
    
    if "^[" in token_to_check:
        idx = token_to_check.rfind("m")
        if idx != -1:
            token_to_check = token_to_check[idx+1:]
    
    analytics, username = read_user_info(token_to_check)
    
    state.token = token_to_check
    state.analytics_token = analytics
    state.username = username
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


def download_games() -> str:
    request = urllib.request.Request(GAMES_CDN_URL, headers={"User-Agent": USER_AGENT})
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
            with console.status("[bold blue]Downloading database...[/bold blue]"):
                raw = download_games()
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
            "rendered_locale": "en-US",
            "launch_signature": self.session.launch_signature,
            "client_app_state": "focused",
            "client_send_timestamp": now,
        }
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
                "game_executable": game.exe,
                "game_detection_enabled": True,
                "initial_heartbeat": initial,
                "final_heartbeat": final,
                "game_session_id": session_id,
                "duration_tracked_ms": duration_ms,
                "launch_signature": self.session.launch_signature,
                "client_app_state": "focused",
                "client_send_timestamp": ts,
            },
        }

    def build_session(self, game: Game, duration_ms: int) -> list[dict]:
        sid = str(uuid.uuid4())
        now = int(time.time() * 1000)
        start = max(0, now - duration_ms)
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
            "accept-language": "en-US",
            "authorization": self.state.token,
            "content-type": "application/json",
            "origin": "https://discord.com",
            "referer": "https://discord.com/channels/@me",
            "user-agent": USER_AGENT,
            "x-discord-locale": "en-US",
            "x-super-properties": self.session.super_props,
        }
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


class TerminalApp:
    def __init__(self) -> None:
        self.state = State.load()
        self.session: Session | None = None
        self.client: ScienceClient | None = None
        self.games: list[Game] = []

    def print_header(self) -> None:
        width = get_term_width()
        console.print(f"[bold magenta]MAX UR BADGES[/bold magenta]".center(width))
        console.print("-" * width, style="grey37")

    def clear(self) -> None:
        console.clear()
        self.print_header()

    def prompt_and_authenticate(self) -> bool:
        try:
            token_input = Prompt.ask("[bold cyan]Enter Discord Token[/bold cyan]", password=False).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            return False

        clean_token = sanitize_input(token_input)
        if not clean_token:
            console.print("[red]Token cannot be empty or contain non-ASCII characters.[/red]")
            return False

        auth_success = False
        error_msg = ""

        with console.status("[blue]Authenticating...[/blue]"):
            try:
                ensure_token(self.state, test_token=clean_token)
                auth_success = True
            except Exception as e:
                error_msg = str(e)

        if auth_success:
            console.print(f"[bold green]OK: Authenticated as {self.state.username}[/bold green]\n")
            time.sleep(1)
            return True
        else:
            console.print(f"[bold red]Authentication failed:[/bold red] {error_msg}")
            console.print("[yellow]The token was invalid and has NOT been saved.[/yellow]")
            return False

    def print_notice(self) -> None:
        console.print("[yellow]NOTICE:[/yellow] Hours take ~24h to update on profile.")

    def start(self) -> None:
        self.clear()
        
        if self.state.has_token:
            auth_ok = False
            err_details = ""
            with console.status("[blue]Authenticating existing token...[/blue]"):
                try:
                    ensure_token(self.state)
                    auth_ok = True
                except Exception as e:
                    err_details = str(e)

            if not auth_ok:
                console.print(f"[red]Saved token invalid:[/red] {err_details}")
                self.state.clear_file()
                self.state = State()
                if not self.prompt_and_authenticate():
                    return
        else:
            if not self.prompt_and_authenticate():
                return

        self.session = Session.new()
        self.client = ScienceClient(self.state, self.session)

        self.games = load_games()
        if not self.games:
            console.print("[red]Failed to load games database.[/red]")
            return

        self.main_menu()

    def view_games(self) -> None:
        self.clear()
        
        table = Table(
            title="Games Database", 
            border_style="grey37", 
            header_style="bold cyan", 
            expand=True
        )
        table.add_column("#", style="dim", width=3, no_wrap=True)
        table.add_column("Title", style="bold white", overflow="ellipsis")
        table.add_column("ID", style="dim", overflow="ellipsis")

        for idx, g in enumerate(self.games[:10], start=1):
            table.add_row(str(idx), g.name, g.id)

        console.print(table)
        console.print(f"\n[dim]Showing 10 / {len(self.games):,} games.[/dim]\n")
        try:
            Prompt.ask("Press Enter to return", default="")
        except (KeyboardInterrupt, EOFError):
            pass

    def run_booster(self) -> None:
        self.clear()
        self.print_notice()
        console.print()

        try:
            hours_str = Prompt.ask(
                "Target Hours", 
                choices=["100", "1000", "5000", "10000"], 
                default="10000"
            )
            batch_size = int(Prompt.ask("Batch Size", default="50"))
            batch_delay = float(Prompt.ask("Delay (s)", default="0.3"))
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Cancelled.[/yellow]")
            return

        hours = float(hours_str)
        duration_ms = int(hours * 3600 * 1000)
        total = len(self.games)

        console.print(f"\n[green]Starting: {total:,} games @ {hours:g}h...[/green]\n")

        sent_ok = 0
        
        progress = Progress(
            SpinnerColumn("line", style="cyan"),
            BarColumn(bar_width=12, complete_style="green", finished_style="green"),
            TextColumn("[cyan]{task.percentage:>3.0f}%[/cyan]"),
            TextColumn("[dim]{task.completed}/{task.total}[/dim]"),
            console=console
        )

        with progress:
            task = progress.add_task("Syncing", total=total)
            
            for request_no, chunk in enumerate(_chunked(self.games, batch_size), start=1):
                events = []
                for game in chunk:
                    events.extend(self.client.build_session(game, duration_ms))
                
                status = self.client.post(events)

                if status == 204:
                    sent_ok += len(chunk)
                    progress.update(task, advance=len(chunk))
                elif status in (401, 403):
                    console.print("\n[red]Token invalid or expired during execution.[/red]")
                    self.state.clear_file()
                    break
                else:
                    console.print(f"\n[yellow]Batch {request_no} returned status {status}[/yellow]")
                
                time.sleep(batch_delay)

        console.print("\n" + "-" * get_term_width(), style="grey37")
        console.print(f"User: [cyan]{self.state.username}[/cyan]")
        console.print(f"Done: [green]{sent_ok:,} / {total:,} games[/green]")
        console.print(f"Target: [yellow]{hours:g} hours/game[/yellow]")
        
        try:
            Prompt.ask("\nPress Enter to return", default="")
        except (KeyboardInterrupt, EOFError):
            pass

    def main_menu(self) -> None:
        while True:
            self.clear()
            console.print(f"Account: [bold cyan]{self.state.username}[/bold cyan] | Loaded: [green]{len(self.games):,}[/green]\n")

            console.print("[cyan]1.[/cyan] Start Booster")
            console.print("[cyan]2.[/cyan] View Games Database")
            console.print("[cyan]3.[/cyan] Change Token")
            console.print("[cyan]4.[/cyan] Exit\n")

            try:
                choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"], default="1")
            except (KeyboardInterrupt, EOFError):
                console.print("\nExiting...\n")
                break

            if choice == "1":
                self.run_booster()
            elif choice == "2":
                self.view_games()
            elif choice == "3":
                if self.prompt_and_authenticate():
                    self.session = Session.new()
                    self.client = ScienceClient(self.state, self.session)
            elif choice == "4":
                console.print("\nExiting...\n")
                break


def main() -> None:
    try:
        TerminalApp().start()
    except (KeyboardInterrupt, EOFError):
        console.print("\nExiting...\n")


if __name__ == "__main__":
    main()

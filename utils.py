import datetime
import subprocess
import time
import socket
from typing import Optional

from config import OLLAMA_MODEL


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


def send_notification(title: str, message: str) -> None:
    """Show macOS notification via AppleScript."""
    try:
        script = f'display notification "{message}" with title "{title}" sound name "Glass"'
        subprocess.run(["osascript", "-e", script])
    except Exception:
        # best-effort, don't crash if notifications fail
        pass


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def manage_ollama(action: str, was_running_initially: bool = False, port: int = 11434) -> Optional[bool]:
    """Start or stop Ollama server.

    - If `action == 'start'`: starts Ollama if not already running and waits for port.
      Returns True if it started Ollama, False if it was already running.
    - If `action == 'stop'`: stops Ollama only if `was_running_initially` is True.
    """
    if action == "start":
        if is_port_open(port):
            return False
        else:
            log(f"Запуск Ollama ({OLLAMA_MODEL})...")
            subprocess.Popen(
                ["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            attempts = 0
            while not is_port_open(port) and attempts < 15:
                time.sleep(2)
                attempts += 1
            return True
    elif action == "stop":
        if was_running_initially:
            try:
                subprocess.run(["pkill", "ollama"], check=False)
            except Exception:
                pass
        return None


def ensure_ollama(port: int = 11434, start_wait_attempts: int = 15) -> bool:
    """Ensure Ollama listening on `port`. Start it if needed and wait until available."""
    if is_port_open(port):
        return True

    log(f"Запуск Ollama ({OLLAMA_MODEL})...")
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for _ in range(start_wait_attempts):
        if is_port_open(port):
            return True
        time.sleep(1)
    return False

import time
from pathlib import Path

from pynput import keyboard
from scapy.all import *

log_dir = Path("Logs/internet")
log_dir.mkdir(parents=True, exist_ok=True)

today_str = time.strftime("%Y-%m-%d")
filename = log_dir / f"{today_str}.txt"


def write_file(file_path, contents):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(contents + "\n")


sniffer = AsyncSniffer(
    prn=lambda packet: write_file(filename, packet.summary())
)


def on_press(key):
    if key == keyboard.Key.esc:
        if sniffer.running:
            sniffer.stop()
        return False  # Stop the keyboard listener


def log_traffic():
    sniffer.start()
    print(f"Sniffing started. Logging to {filename}... Press Esc to stop.")
def stopSniffer():
    sniffer.stop()
    print(f"Stopped sniffer.")
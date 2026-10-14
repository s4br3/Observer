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

def log_traffic():
    sniffer.start()
    print(f"Sniffing started. Logging to {filename}... Press Esc to stop.")
def stopSniffer():
    if sniffer.running:
        sniffer.stop()
        print("Sniffing stopped.")
    else:
        print("Sniffer is not running.")
import time
from pathlib import Path

from pynput import keyboard
from scapy.all import AsyncSniffer

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
        return False  # Stop the keyboard listener


def log_traffic():
    sniffer.start()
    print(f"Sniffing started. Logging to {filename}... Press Esc to stop.")

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

    if sniffer.running:
        sniffer.stop()

    print("\nSniffing stopped.")


if __name__ == "__main__":
    log_traffic()

import time
from pathlib import Path
from scapy.all import *

log_dir = Path("Logs/internet")
log_dir.mkdir(exist_ok=True)

today_str = time.strftime("%Y-%m-%d")
filename = log_dir / f"{today_str}.txt"

def writeFile(file_path, contents):
    with open(file_path, 'a+', encoding='utf-8') as f:
        f.write(contents + "\n")

sniffer = AsyncSniffer(prn=lambda x: writeFile(filename, x.summary()))
sniffer.start()

print(f"Sniffing started. Logging to {filename}...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    sniffer.stop()
    print("\nSniffing stopped.")
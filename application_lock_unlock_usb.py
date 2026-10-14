"""
Access & Security Monitor
----------------------------
A transparent activity/security logger for a shared or company device.
Logs to access_log.txt:
  - Lock / unlock / logon / logoff of the Windows session
  - Which application is in the foreground, and its window title
  - USB mass-storage devices being connected or removed
  - Files above a size threshold appearing/changing in watched folders
    (a simple signal for "someone copied a large amount of data")

It does NOT capture keystrokes, passwords, clipboard contents, screen
content, or file contents. Only metadata: names, sizes, timestamps.

IMPORTANT if deploying this on employee machines:
  - This should only run with each employee's informed, documented consent
    (e.g. signed acknowledgment of a monitoring policy), not silently.
  - It should be disclosed what is and isn't collected (see list above).
  - Consider legal review for your jurisdiction (UK GDPR / US state laws
    on workplace monitoring often require necessity + proportionality +
    advance notice). This script intentionally avoids keystroke/content
    capture to stay on the less invasive end of that spectrum, but that
    doesn't substitute for an actual compliance review.

Requirements:
  pip install pywin32 psutil watchdog

Run:
  python access_monitor.py
  (visible console window; Ctrl+C to stop)
"""

import ctypes
import datetime
import getpass
import os
import sys
import threading

import psutil
import win32con
import win32gui
import win32process
import win32ts
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_log.txt")
LOG_WINDOW_TITLE = True
HEARTBEAT_SECONDS = 300

# Folders to watch for large file writes (edit this list for your setup).
# Defaults to the current user's Desktop/Documents/Downloads.
WATCHED_FOLDERS = [
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.path.expanduser("~"), "Documents"),
    os.path.join(os.path.expanduser("~"), "Downloads"),
]
LARGE_FILE_THRESHOLD_MB = 50  # flag files at or above this size

NOTIFY_FOR_THIS_SESSION = 0

WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
WTS_SESSION_LOGON = 0x5
WTS_SESSION_LOGOFF = 0x6
EVENT_NAMES = {
    WTS_SESSION_LOCK: "LOCKED",
    WTS_SESSION_UNLOCK: "UNLOCKED",
    WTS_SESSION_LOGON: "LOGON",
    WTS_SESSION_LOGOFF: "LOGOFF",
}

EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000

# USB / device-change constants (from Windows' dbt.h)
WM_DEVICECHANGE = 0x0219
DBT_DEVICEARRIVAL = 0x8000         # a device was connected
DBT_DEVICEREMOVECOMPLETE = 0x8004  # a device was removed
DBT_DEVTYP_VOLUME = 0x00000002     # the device is a drive/volume (e.g. USB stick)


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def log_line(text: str) -> None:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {text}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_session_event(event_name: str) -> None:
    log_line(f"{event_name} - user: {getpass.getuser()}")


def get_foreground_app_info():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None, None
    window_title = win32gui.GetWindowText(hwnd)
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process_name = psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        process_name = "unknown"
    return process_name, window_title


def get_drive_letter_from_devicechange(lparam):
    """
    When Windows sends a DBT_DEVICEARRIVAL/REMOVAL message for a volume,
    `lparam` points to a DEV_BROADCAST_VOLUME structure whose `unitmask`
    field is a bitmask of drive letters (bit 0 = A:, bit 1 = B:, ...).
    This reads that structure and returns the drive letter(s) as a string.
    """
    class DEV_BROADCAST_VOLUME(ctypes.Structure):
        _fields_ = [
            ("dbcv_size", ctypes.c_ulong),
            ("dbcv_devicetype", ctypes.c_ulong),
            ("dbcv_reserved", ctypes.c_ulong),
            ("dbcv_unitmask", ctypes.c_ulong),
        ]

    try:
        vol = ctypes.cast(lparam, ctypes.POINTER(DEV_BROADCAST_VOLUME)).contents
        if vol.dbcv_devicetype != DBT_DEVTYP_VOLUME:
            return None
        letters = []
        for i in range(26):
            if vol.dbcv_unitmask & (1 << i):
                letters.append(f"{chr(ord('A') + i)}:")
        return ", ".join(letters) if letters else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Large-file watcher (watchdog)
# ---------------------------------------------------------------------------

class LargeFileHandler(FileSystemEventHandler):
    """
    Fires on file create/modify events inside a watched folder. If the file
    is at or above LARGE_FILE_THRESHOLD_MB, log it. This is a simple proxy
    for "a meaningful chunk of data was written" — e.g. exporting a database
    dump, copying a large archive to a USB drive staging folder, etc.
    We only log the file's path, name, and size — never its contents.
    """

    def _check(self, path, action):
        try:
            if os.path.isdir(path):
                return
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb >= LARGE_FILE_THRESHOLD_MB:
                log_line(f"LARGE_FILE_{action} - {path} - {size_mb:.1f} MB")
        except OSError:
            # File may have been deleted/moved between the event firing
            # and us checking its size — just skip it.
            pass

    def on_created(self, event):
        if not event.is_directory:
            self._check(event.src_path, "CREATED")

    def on_modified(self, event):
        if not event.is_directory:
            self._check(event.src_path, "MODIFIED")


def start_file_watcher():
    observer = Observer()
    handler = LargeFileHandler()
    watched_count = 0
    for folder in WATCHED_FOLDERS:
        if os.path.isdir(folder):
            observer.schedule(handler, folder, recursive=True)
            watched_count += 1
            print(f"[OK] Watching folder: {folder}")
        else:
            print(f"[SKIP] Folder not found: {folder}")
    observer.start()
    print(f"[OK] Large-file watcher running on {watched_count} folder(s), "
          f"threshold {LARGE_FILE_THRESHOLD_MB} MB")
    return observer


# ---------------------------------------------------------------------------
# The main monitor window (session + foreground app + USB)
# ---------------------------------------------------------------------------

class AccessMonitorWindow:

    def __init__(self):
        print("=== Startup self-check ===")

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.wnd_proc
        wc.lpszClassName = "AccessMonitorWindow"
        wc.hInstance = win32gui.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(
            class_atom, "Access Monitor", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None,
        )
        print("[OK] Message window created" if self.hwnd else "[FAIL] Window creation failed")

        try:
            win32ts.WTSRegisterSessionNotification(self.hwnd, NOTIFY_FOR_THIS_SESSION)
            print("[OK] Subscribed to session lock/unlock notifications")
        except Exception as e:
            print(f"[FAIL] Session notification subscription failed: {e}")
            raise

        self._win_event_proc = ctypes.WINFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p,
            ctypes.c_long, ctypes.c_long, ctypes.c_ulong, ctypes.c_ulong
        )(self.win_event_callback)
        self._hook = ctypes.windll.user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
            0, self._win_event_proc, 0, 0, WINEVENT_OUTOFCONTEXT,
        )
        print("[OK] Subscribed to foreground-window-change notifications" if self._hook
              else "[FAIL] Foreground hook failed")

        # USB/device-change notifications arrive via WM_DEVICECHANGE, which
        # every window receives automatically once it exists — no separate
        # registration call needed, unlike the two above.
        print("[OK] Ready to receive USB/device-change notifications (WM_DEVICECHANGE)")

        test_app, _ = get_foreground_app_info()
        print(f"[OK] Foreground read test succeeded: {test_app}" if test_app
              else "[FAIL] Could not read foreground window")

        self._file_observer = start_file_watcher()

        print("=== Self-check complete ===\n")

        self._last_app = None
        print(f"Monitor running. Logging to: {LOG_FILE}")
        print("Press Ctrl+C in this console to stop.\n")

        log_session_event("MONITOR_STARTED")
        self._log_current_foreground()

        self._stop_heartbeat = threading.Event()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _heartbeat_loop(self):
        while not self._stop_heartbeat.wait(HEARTBEAT_SECONDS):
            log_line("HEARTBEAT - monitor is running")

    def _log_current_foreground(self):
        process_name, window_title = get_foreground_app_info()
        if process_name and process_name != self._last_app:
            self._last_app = process_name
            msg = f"APP_FOREGROUND - {process_name}"
            if LOG_WINDOW_TITLE and window_title:
                msg += f' - title: "{window_title}"'
            log_line(msg)

    def win_event_callback(self, hWinEventHook, event, hwnd, idObject, idChild, idEventThread, dwmsEventTime):
        if event == EVENT_SYSTEM_FOREGROUND:
            self._log_current_foreground()

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_WTSSESSION_CHANGE:
            event_name = EVENT_NAMES.get(wparam, f"UNKNOWN_EVENT_{wparam}")
            log_session_event(event_name)
            return 0

        elif msg == WM_DEVICECHANGE:
            # wparam tells us whether a device arrived or was removed.
            if wparam == DBT_DEVICEARRIVAL:
                drives = get_drive_letter_from_devicechange(lparam)
                if drives:
                    log_line(f"USB_CONNECTED - drive(s): {drives}")
            elif wparam == DBT_DEVICEREMOVECOMPLETE:
                drives = get_drive_letter_from_devicechange(lparam)
                if drives:
                    log_line(f"USB_REMOVED - drive(s): {drives}")
            return 1  # per Windows docs, return TRUE (1) for WM_DEVICECHANGE

        elif msg == win32con.WM_DESTROY:
            win32ts.WTSUnRegisterSessionNotification(hwnd)
            ctypes.windll.user32.UnhookWinEvent(self._hook)
            self._file_observer.stop()
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def run(self):
        win32gui.PumpMessages()


def main():
    if sys.platform != "win32":
        print("This tool only works on Windows (uses WTS, WinEvent, and device-change APIs).")
        sys.exit(1)

    monitor = AccessMonitorWindow()
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor._stop_heartbeat.set()
        monitor._file_observer.stop()
        log_session_event("MONITOR_STOPPED")
        print("\nStopped.")


if __name__ == "__main__":
    main()
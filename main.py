from pynput import keyboard, mouse
from datetime import datetime

def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# --- Mouse Callbacks ---
def on_move(x, y):
    print(f'Pointer moved to ({x}, {y}) - {get_timestamp()}')

def on_click(x, y, button, pressed):
    state = 'Pressed' if pressed else 'Released'
    print(f'{state} {button} at ({x}, {y}) - {get_timestamp()}')

def on_scroll(x, y, dx, dy):
    direction = 'down' if dy < 0 else 'up'
    print(f'Scrolled {direction} at ({x}, {y}) - {get_timestamp()}')

# --- Placeholders for listeners ---
mouse_listener = None
keyboard_listener = None

# --- Keyboard Callback ---
def on_press(key):
    try:
        print(f'Key pressed: {key.char} - {get_timestamp()}')
    except AttributeError:
        print(f'Special key pressed: {key} - {get_timestamp()}')

    if key == keyboard.Key.esc:
        print("Exiting listeners...")
        if mouse_listener:
            mouse_listener.stop()  # Stop the mouse listener
        return False               # Stop the keyboard listener

# --- Initialize Listeners ---
mouse_listener = mouse.Listener(
    on_move=on_move, 
    on_click=on_click, 
    on_scroll=on_scroll
)
keyboard_listener = keyboard.Listener(
    on_press=on_press
)

# --- Start Concurrently ---
keyboard_listener.start()
mouse_listener.start()

print("Listeners are running concurrently. Press ESC to exit.")

# --- Keep alive until ESC is pressed ---
keyboard_listener.join()
mouse_listener.join()

print("Program exited cleanly.")
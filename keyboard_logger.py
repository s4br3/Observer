from pynput import keyboard


#keylogger function
def on_press(key):

    try:
        #print regular keys
        print(f'Key pressed: {key.char}')

    except AttributeError:
        #print special keys
        print(f'Special key pressed: {key}')

    if key == keyboard.Key.esc:
        print("Exiting listener...")
        return False  # Returning False stops the listener loop

# Using a context manager ('with') handles starting and joining automatically
with keyboard.Listener(on_press=on_press) as listener:
  listener.join()


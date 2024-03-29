import pyperclip
from pynput.mouse import Listener as MouseListener, Button, Controller as MouseController
from pynput.keyboard import Listener as KeyboardListener, Key, KeyCode, Controller as KeyboardController
import time
import os
from threading import Thread
import requests
import tkinter as tk
import pystray
from PIL import Image

LAST_CLICK_TIME = 0
DOUBLE_CLICK_THRESHOLD = 0.20

keyboard = KeyboardController()
mouse = MouseController()

currently_pressed_keys = set()

# Exit program combinations
CLOSE_PROGRAM_COMBINATIONS = [
    {Key.alt_l, KeyCode(char='0')}
]

# Search combinations
SEARCH_COMBINATIONS = [
    {Key.alt_l, KeyCode(char='c')}
]

def create_window(input):
    """Create a popup window with the given input
    
    Arguments:
        input {string} -- The input to be typed
        
        Returns:
        None
    """

    x, y = mouse.position
    window = tk.Tk()
    window.withdraw() # Hide window

    width = 20 + len(input) * 6 # width for the Tk root
    height = 40 # height for the Tk root
    y_offset = 20 # Offset from mouse

    # calculate x and y coordinates for the Tk root window
    x = x - width / 2
    y = y - height - y_offset

    # set the dimensions of the screen and where it is placed
    window.geometry('%dx%d+%d+%d' % (width, height, x, y))
    window.overrideredirect(1) #Remove border
    close = tk.Button(window, text = input, command = lambda: on_confirm())
    close.pack(fill = tk.BOTH, expand = 1)

    window.focus_force() # Focus on window

    # destroy window when it loses focus
    window.bind("<FocusOut>", lambda _: window.destroy())  # User focus on another window
    window.bind("<Escape>", lambda _: window.destroy())    # User press Escape
    window.protocol("WM_DELETE_WINDOW", lambda _: window.destroy())

    def on_confirm():
        window.destroy()
        pyperclip.copy(input)
        keyboard.type(input)

    window.deiconify() # Show window
    window.mainloop()


def on_click(x, y, button, pressed):
    """Called when a mouse button is clicked
    
    Arguments:
        x {int} -- The x position of the mouse
        y {int} -- The y position of the mouse
        button {Button} -- The button that was clicked
        pressed {bool} -- Whether the button was pressed or released
        
        Returns:
        None
    """

    global LAST_CLICK_TIME
    if button == Button.left and not pressed:
        click_time = time.time()  # Get the current time
        if click_time - LAST_CLICK_TIME < DOUBLE_CLICK_THRESHOLD and click_time - LAST_CLICK_TIME > 0:
            create_popup()
        LAST_CLICK_TIME = click_time  # Update the last click time

def search():
    """Search for the first suggestion in the clipboard
    
    Returns:
        string -- The first suggestion

        None -- If no suggestion is found
    """

    text = copy_clipboard()
    text = text.strip()
    if text == "" or text == "\r\n": return # Empty clipboard
    data = query_suggestion_data(text) 
    if data == None or data[1] == []: return # No suggestions
    return data[1][0] # Return first suggestion

def create_popup():
    """Create a popup window with the first suggestion in the clipboard

    Returns:
        None
    """
    
    suggestion = search()
    if suggestion == None: return
    create_window(suggestion)

def query_suggestion_data(query):
    """Query Google for suggestions

    Arguments:
        query {string} -- The query to search for

    Returns:
        json -- The response from Google
    """

    url = "http://suggestqueries.google.com/complete/search"
    params = {
        "client": "firefox",
        "q": query
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # raise an exception if the response contains an HTTP error status code
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

    return response.json() 

def copy_clipboard():
    """Copy the clipboard to a variable

    Returns:
        string -- The clipboard
    """

    pyperclip.copy("")

    # Release all pressed keys before copying
    for key in currently_pressed_keys:
        keyboard.release(key)

    keyboard.press(Key.ctrl.value)
    keyboard.press('c')
    keyboard.release('c')
    keyboard.release(Key.ctrl.value)
    time.sleep(.01)  # ctrl-c is usually very fast but your program may execute faster
    return pyperclip.paste()

def on_press(key):
    """Called when a key is pressed
    
    Arguments:
        key {Key} -- The key that was pressed
        
    Returns:
        None
    """
    currently_pressed_keys.add(key)
    if any(all(k in currently_pressed_keys for k in COMBO) for COMBO in CLOSE_PROGRAM_COMBINATIONS):
        quit()
    elif any(all(k in currently_pressed_keys for k in COMBO) for COMBO in SEARCH_COMBINATIONS):
        create_popup()
        currently_pressed_keys.clear()

def quit():
    print("Quitting...")
    os._exit(0)

def on_release(key):
    """Called when a key is released

    Arguments:
        key {Key} -- The key that was released

    Returns:
        None
    """
    if key in currently_pressed_keys:
        currently_pressed_keys.remove(key)

def create_tray_icon():
    """Create a tray icon

    Returns:
        None
    """

    image = Image.open("./static/images/favicon.ico")
    menu = pystray.Menu(
        pystray.MenuItem('Quit', quit)
    )
    
    icon = pystray.Icon("Suggestion App", image, "Suggestion App", menu=menu)
    icon.run()

global mouse_listener, keyboard_listener

def main():
    """Main function"""

    global ctrl_pressed, mouse_listener, keyboard_listener
    ctrl_pressed = False

    mouse_listener = MouseListener(on_click=on_click)
    keyboard_listener = KeyboardListener(on_press=on_press, on_release=on_release)

    mouse_thread = Thread(target=mouse_listener.start)
    keyboard_thread = Thread(target=keyboard_listener.start)

    mouse_thread.start()
    keyboard_thread.start()

    mouse_thread.join()
    keyboard_thread.join()

    create_tray_icon()

    while True:
        time.sleep(1)  # keep program running to allow keyboard listener to work

if __name__ == "__main__":
    main()
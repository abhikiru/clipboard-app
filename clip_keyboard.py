import keyboard
import mouse
import pyperclip
import time
import threading
import requests

# Configuration
API_BASE_URL = "https://clipboard-app-seven.vercel.app"  # Your Vercel URL

# Global variables
script_text = ""  # Clipboard content
text_index = 0  # Current typing position
auto_typing = False  # Automatic typing toggle
typing_speed = 0.3  # Default typing speed in seconds (delay between characters)
manual_typing_lock = threading.Lock()  # Prevent overlapping Insert key handling
clipboard_lock = threading.Lock()  # Lock for clipboard access
username = None  # Store authenticated username

# Function to authenticate user
def authenticate():
    global username
    print("\n=== Login ===")
    username_input = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    if not username_input or not password:
        print("Error: Username and password cannot be empty.")
        return False

    try:
        print(f"Sending authentication request for username: {username_input}")
        response = requests.post(
            f"{API_BASE_URL}/api/authenticate",
            data={"username": username_input, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        response.raise_for_status()
        data = response.json()

        if data["status"] == "success":
            username = data["username"]
            print(f"\nWelcome, {username}!")
            return True
        else:
            print(f"Error: {data['message']}")
            return False
    except requests.RequestException as e:
        print(f"Error: Failed to connect to server: {e}")
        return False

# Function to handle new line actions
def handle_new_line():
    time.sleep(0.1)  # Simulate typing delay
    keyboard.press_and_release('enter')  # Press Enter to move to a new line
    time.sleep(0.1)
    keyboard.press_and_release('ctrl+backspace')  # Remove blank spaces
    time.sleep(0.1)

# Function for manual typing (Insert key)
def type_one_character():
    global text_index, script_text
    with manual_typing_lock:  # Prevent overlapping Insert key presses
        if text_index < len(script_text):
            char_to_type = script_text[text_index]

            # Handle new line
            if char_to_type == '\n':
                handle_new_line()

            # Type the character
            keyboard.write(char_to_type)
            text_index += 1
            print(f"[DEBUG] Typed: {char_to_type}")
        else:
            print("[DEBUG] Typing complete.")

# Function for automatic typing
def automatic_typing():
    global auto_typing, text_index, script_text
    while auto_typing:
        if text_index < len(script_text):
            char_to_type = script_text[text_index]

            # Handle new line
            if char_to_type == '\n':
                handle_new_line()

            # Type the character
            keyboard.write(char_to_type)
            text_index += 1
            time.sleep(typing_speed)  # Simulate human typing speed
        else:
            auto_typing = False  # Stop when typing is complete
            print("[DEBUG] Automatic typing complete.")
            keyboard.press_and_release('enter')  # Move to the next line after completion

# Function to toggle automatic typing
def toggle_auto_typing():
    global auto_typing
    if not auto_typing:
        auto_typing = True
        print("[DEBUG] Automatic typing started.")
        threading.Thread(target=automatic_typing, daemon=True).start()
    else:
        auto_typing = False
        print("[DEBUG] Automatic typing stopped.")

# Function to reset typing to the beginning
def reset_typing():
    global text_index
    text_index = 0
    print("[DEBUG] Typing reset to the beginning.")

# Function to monitor clipboard for updates
def monitor_clipboard():
    global script_text, text_index
    while True:
        with clipboard_lock:
            new_text = pyperclip.paste()
            if new_text != script_text:
                script_text = new_text
                text_index = 0  # Reset position when clipboard updates
                print(f"[DEBUG] Clipboard updated: {script_text}")
        time.sleep(0.5)  # Check every 500ms

# Function to adjust typing speed
def increase_typing_speed():
    global typing_speed
    typing_speed = max(0.05, typing_speed - 0.05)  # Minimum delay of 0.05s
    print(f"[DEBUG] Typing speed increased: {typing_speed:.2f}s delay.")

def decrease_typing_speed():
    global typing_speed
    typing_speed = min(1.0, typing_speed + 0.05)  # Maximum delay of 1.0s
    print(f"[DEBUG] Typing speed decreased: {typing_speed:.2f}s delay.")

# Function to handle mouse wheel events
def handle_mouse_event(event):
    if isinstance(event, mouse.WheelEvent):  # Handle scroll events
        if event.delta > 0:  # Scroll forward
            increase_typing_speed()
        elif event.delta < 0:  # Scroll backward
            decrease_typing_speed()

# Start clipboard monitoring in a separate thread
def start_clipboard_monitor():
    monitor_thread = threading.Thread(target=monitor_clipboard, daemon=True)
    monitor_thread.start()

# Main execution
if __name__ == "__main__":
    # Authenticate user before proceeding
    if not authenticate():
        print("Login failed. Exiting script.")
        exit(1)

    print("[INFO] Typing script initialized.")
    print("Press 'Insert' to type one character at a time from the clipboard.")
    print("Press 'Ctrl+B' to start/stop automatic typing.")
    print("Press '$' to stop automatic typing.")
    print("Press 'Ctrl+M' to reset typing to the beginning.")
    print("Use the scroll wheel to adjust typing speed (up: faster, down: slower).")

    # Keyboard hotkey setup
    keyboard.add_hotkey('insert', type_one_character)  # Manual typing with Insert key
    keyboard.add_hotkey('ctrl+b', toggle_auto_typing)  # Toggle auto typing
    keyboard.add_hotkey('$', lambda: toggle_auto_typing() if auto_typing else None)  # Stop auto typing with $
    keyboard.add_hotkey('ctrl+m', reset_typing)  # Reset typing to the beginning

    # Set up mouse hook for handling events
    mouse.hook(handle_mouse_event)  # Hook to monitor all mouse events

    # Start clipboard monitoring
    start_clipboard_monitor()

    try:
        while True:
            time.sleep(1)  # Prevent high CPU usage
    except KeyboardInterrupt:
        print("[INFO] Typing script terminated.")
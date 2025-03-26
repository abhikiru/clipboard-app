import requests
import pyperclip
import json
import threading
import time
import websocket
import rel

# Configuration
API_BASE_URL = "http://localhost:8000"  # Change this to your deployed server URL (e.g., Heroku/Render URL)
WS_URL = "ws://localhost:8000/ws"  # Change this to your deployed WebSocket URL

class ClipboardManager:
    def __init__(self):
        self.username = None
        self.role = None
        self.copied_text_history = []
        self.clipboard_monitor_thread = None
        self.running = False
        self.last_clipboard_content = None
        self.ws = None

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            if data.get("action") == "clipboard_update":
                text = data.get("text")
                pyperclip.copy(text)
                print(f"Copied to system clipboard: {text}")
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")

    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"[WebSocket] Error: {error}")
        self.reconnect()

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket closure."""
        print(f"[WebSocket] Connection closed: {close_status_code} - {close_msg}")
        self.reconnect()

    def on_open(self, ws):
        """Handle WebSocket connection opening."""
        print(f"[WebSocket] Connection established for user: {self.username}")

    def reconnect(self):
        """Reconnect to WebSocket after a delay."""
        if not self.running:
            return
        print("Attempting to reconnect in 5 seconds...")
        time.sleep(5)
        self.start_websocket()

    def start_websocket(self):
        """Start WebSocket connection."""
        if not self.username:
            print("Error: Username not set. Cannot start WebSocket.")
            return
        ws_url = f"{WS_URL}/{self.username}"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        threading.Thread(target=self.ws.run_forever, kwargs={"ping_interval": 30, "ping_timeout": 10}, daemon=True).start()

    def monitor_clipboard(self):
        """Monitor the system clipboard for changes and send updates to the server."""
        print("Starting clipboard monitoring...")
        self.last_clipboard_content = pyperclip.paste()
        while self.running:
            try:
                current_content = pyperclip.paste()
                if current_content != self.last_clipboard_content and current_content.strip():
                    print(f"New clipboard content detected: {current_content}")
                    self.last_clipboard_content = current_content
                    self.submit_text_to_server(current_content)
            except Exception as e:
                print(f"Error monitoring clipboard: {e}")
            time.sleep(1)

    def start_clipboard_monitoring(self):
        """Start the clipboard monitoring thread."""
        self.running = True
        self.clipboard_monitor_thread = threading.Thread(target=self.monitor_clipboard)
        self.clipboard_monitor_thread.daemon = True
        self.clipboard_monitor_thread.start()

    def stop_clipboard_monitoring(self):
        """Stop the clipboard monitoring thread."""
        self.running = False
        if self.clipboard_monitor_thread:
            self.clipboard_monitor_thread.join()
        if self.ws:
            self.ws.close()

    def authenticate(self):
        print("\n=== Login ===")
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()

        if not username or not password:
            print("Error: Username and password cannot be empty.")
            return False

        try:
            print(f"Sending authentication request for username: {username}")
            response = requests.post(
                f"{API_BASE_URL}/api/authenticate",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text}")
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success":
                self.username = data["username"]
                self.role = data["role"]
                print(f"\nWelcome, {self.username}! (Role: {self.role})")
                return True
            else:
                print(f"Error: {data['message']}")
                return False
        except requests.RequestException as e:
            print(f"Error: Failed to connect to server: {e}")
            return False

    def load_clipboard_data(self):
        if not self.username:
            print("Error: Not logged in.")
            return False

        try:
            response = requests.get(f"{API_BASE_URL}/api/copied_text_history/{self.username}")
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success":
                self.copied_text_history = data["copied_text_history"]
                if self.copied_text_history:
                    most_recent_item = self.copied_text_history[0]
                    pyperclip.copy(most_recent_item)
                    print(f"Automatically copied most recent item to clipboard: {most_recent_item}")
                else:
                    print("No items in copied text history to copy.")
                return True
            else:
                print(f"Error: {data['message']}")
                return False
        except requests.RequestException as e:
            print(f"Error: Failed to connect to server: {e}")
            return False

    def submit_text_to_server(self, text):
        """Submit text to the server."""
        if not text:
            print("Error: Text cannot be empty.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/submit_copied_text/{self.username}",
                json={"text": text}
            )
            response.raise_for_status()
            data = response.json()
            if data["status"] == "success":
                print(f"Text submitted to copied_text_history successfully: {text}")
            else:
                print(f"Error: {data['message']}")
        except requests.RequestException as e:
            print(f"Error: Failed to connect to server: {e}")

    def run(self):
        print("Welcome to Clipboard Manager!")
        while True:
            if not self.username:
                if not self.authenticate():
                    print("Login failed. Please try again.")
                    continue
                if not self.load_clipboard_data():
                    print("Failed to load clipboard data. Please try again.")
                    self.username = None
                    continue
                self.start_clipboard_monitoring()
                self.start_websocket()
            try:
                print("Clipboard Manager is running. Press Ctrl+C to exit.")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nExiting Clipboard Manager. Goodbye!")
                self.stop_clipboard_monitoring()
                break

if __name__ == "__main__":
    app = ClipboardManager()
    app.run()
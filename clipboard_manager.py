import requests
import pyperclip
import websocket
import json
import threading
import time

# Configuration
API_BASE_URL = "https://clipboard-rbvg372nu-abhishek-sharmas-projects-2069d670.vercel.app"
WS_URL = "wss://clipboard-rbvg372nu-abhishek-sharmas-projects-2069d670.vercel.app/ws"

class ClipboardManager:
    def __init__(self):
        self.username = None
        self.role = None
        self.history = []
        self.copied_text_history = []
        self.ws = None
        self.ws_thread = None
        self.clipboard_monitor_thread = None
        self.running = False
        self.last_clipboard_content = None

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        data = json.loads(message)
        print(f"\n[WebSocket] Received update: {data}")
        if data["type"] == "ping":
            ws.send(json.dumps({"type": "pong"}))
            return
        if data["type"] == "history_update":
            self.history.insert(0, data["text"])
            print(f"New history item added: {data['text']}")
        elif data["type"] == "copied_text_update":
            self.copied_text_history.insert(0, data["text"])
            print(f"New copied text item added: {data['text']}")
        elif data["type"] == "copy_to_clipboard":
            pyperclip.copy(data["text"])
            print(f"Copied to system clipboard: {data['text']}")
        elif data["type"] == "history_delete":
            if data["text"] in self.history:
                self.history.remove(data["text"])
                print(f"History item deleted: {data['text']}")
        elif data["type"] == "copied_text_delete":
            if data["text"] in self.copied_text_history:
                self.copied_text_history.remove(data["text"])
                print(f"Copied text item deleted: {data['text']}")
        elif data["type"] == "history_clear":
            self.history = []
            print("History cleared")
        elif data["type"] == "copied_text_clear":
            self.copied_text_history = []
            print("Copied text history cleared")

    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"[WebSocket] Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket closure."""
        print(f"[WebSocket] Connection closed: {close_status_code} - {close_msg}")

    def on_open(self, ws):
        """Handle WebSocket connection opening."""
        print(f"[WebSocket] Connected to server for user: {self.username}")

    def start_websocket(self):
        """Start the WebSocket connection in a separate thread."""
        if not self.username:
            print("Error: Cannot start WebSocket without logging in.")
            return

        ws_url = f"{WS_URL}/{self.username}"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def monitor_clipboard(self):
        """Monitor the system clipboard for changes and send updates to the server."""
        print("Starting clipboard monitoring...")
        self.last_clipboard_content = pyperclip.paste()  # Initialize with current clipboard content
        while self.running:
            try:
                current_content = pyperclip.paste()
                if current_content != self.last_clipboard_content and current_content.strip():
                    print(f"New clipboard content detected: {current_content}")
                    self.last_clipboard_content = current_content
                    # Submit the new clipboard content to the server
                    self.submit_text_to_server(current_content, history_type="copied_text_history")
            except Exception as e:
                print(f"Error monitoring clipboard: {e}")
            time.sleep(1)  # Check every second to avoid excessive CPU usage

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

    def authenticate(self):
        print("\n=== Login ===")
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()

        if not username or not password:
            print("Error: Username and password cannot be empty.")
            return False

        # Make API request to authenticate
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
                # Start WebSocket connection after successful login
                self.start_websocket()
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

        # Fetch clipboard data from the API
        try:
            response = requests.get(f"{API_BASE_URL}/api/history/{self.username}")
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success":
                self.history = data["history"]
                self.copied_text_history = data["copied_text_history"]
                return True
            else:
                print(f"Error: {data['message']}")
                return False
        except requests.RequestException as e:
            print(f"Error: Failed to connect to server: {e}")
            return False

    def submit_text_to_server(self, text, history_type="history"):
        """Submit text to the server without user interaction."""
        if not text:
            print("Error: Text cannot be empty.")
            return

        endpoint = "/api/submit" if history_type == "history" else "/api/submit_copied_text"
        try:
            response = requests.post(
                f"{API_BASE_URL}{endpoint}/{self.username}",
                json={"text": text}
            )
            response.raise_for_status()
            data = response.json()
            if data["status"] == "success":
                print(f"Text submitted to {history_type} successfully: {text}")
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
                # Start clipboard monitoring after successful login
                self.start_clipboard_monitoring()
            # Keep the app running until the user presses Ctrl+C
            try:
                print("Clipboard Manager is running. Press Ctrl+C to exit.")
                while True:
                    time.sleep(1)  # Keep the main thread alive
            except KeyboardInterrupt:
                print("\nExiting Clipboard Manager. Goodbye!")
                if self.ws:
                    self.ws.close()
                self.stop_clipboard_monitoring()
                break

if __name__ == "__main__":
    app = ClipboardManager()
    app.run()
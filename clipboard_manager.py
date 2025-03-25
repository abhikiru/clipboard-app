import requests
import pyperclip
import websocket
import json
import threading

# Configuration
API_BASE_URL = "https://clipboard-app-seven.vercel.app"
WS_URL = "wss://clipboard-app-seven.vercel.app/ws"

class ClipboardManager:
    def __init__(self):
        self.username = None
        self.role = None
        self.history = []
        self.copied_text_history = []
        self.ws = None
        self.ws_thread = None

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        data = json.loads(message)
        print(f"\n[WebSocket] Received update: {data}")
        if data["type"] == "history_update":
            self.history.insert(0, data["text"])
            print(f"New history item added: {data['text']}")
        elif data["type"] == "copied_text_update":
            self.copied_text_history.insert(0, data["text"])
            print(f"New copied text item added: {data['text']}")
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

    def display_history(self, history_type="history"):
        if history_type == "history":
            items = self.history
            print("\n=== Your History ===")
        else:
            items = self.copied_text_history
            print("\n=== Your Copied Text History ===")

        if not items:
            print("No items found.")
            return

        for i, item in enumerate(items, 1):
            print(f"{i}. {item}")

    def copy_to_clipboard(self, history_type="history"):
        self.display_history(history_type)
        items = self.history if history_type == "history" else self.copied_text_history

        if not items:
            return

        try:
            choice = int(input("\nEnter the number of the item to copy (0 to cancel): "))
            if choice == 0:
                return
            if 1 <= choice <= len(items):
                text = items[choice - 1]
                pyperclip.copy(text)
                print(f"Copied to clipboard: {text}")
            else:
                print("Error: Invalid selection.")
        except ValueError:
            print("Error: Please enter a valid number.")

    def submit_text(self, history_type="history"):
        text = input("\nEnter text to submit: ").strip()
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
                print("Text submitted successfully!")
                # No need to refresh the list manually; WebSocket will handle updates
            else:
                print(f"Error: {data['message']}")
        except requests.RequestException as e:
            print(f"Error: Failed to connect to server: {e}")

    def main_menu(self):
        while True:
            print("\n=== Clipboard Manager ===")
            print(f"Logged in as: {self.username} ({self.role})")
            print("1. View History")
            print("2. View Copied Text History")
            print("3. Copy from History")
            print("4. Copy from Copied Text History")
            print("5. Submit New Text to History")
            print("6. Submit New Text to Copied Text History")
            print("7. Refresh Data")
            print("8. Logout")
            print("9. Exit")

            choice = input("Enter your choice (1-9): ").strip()

            if choice == "1":
                self.display_history("history")
            elif choice == "2":
                self.display_history("copied_text_history")
            elif choice == "3":
                self.copy_to_clipboard("history")
            elif choice == "4":
                self.copy_to_clipboard("copied_text_history")
            elif choice == "5":
                self.submit_text("history")
            elif choice == "6":
                self.submit_text("copied_text_history")
            elif choice == "7":
                if self.load_clipboard_data():
                    print("Data refreshed successfully.")
            elif choice == "8":
                print(f"Goodbye, {self.username}!")
                if self.ws:
                    self.ws.close()
                self.username = None
                self.role = None
                self.history = []
                self.copied_text_history = []
                return True  # Return to login screen
            elif choice == "9":
                print("Exiting Clipboard Manager. Goodbye!")
                if self.ws:
                    self.ws.close()
                return False  # Exit the app
            else:
                print("Error: Invalid choice. Please try again.")

    def run(self):
        print("Welcome to Clipboard Manager!")
        while True:
            if not self.username:
                if not self.authenticate():
                    continue
                if not self.load_clipboard_data():
                    print("Failed to load clipboard data. Please try again.")
                    self.username = None
                    continue
            if not self.main_menu():
                break

if __name__ == "__main__":
    app = ClipboardManager()
    app.run()
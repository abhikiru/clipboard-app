import os
import requests
import pyperclip
import websocket
import json
import threading
import time

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://clipboard-a6qozbmi4-abhishek-sharmas-projects-2069d670.vercel.app")

class ClipboardManager:
    def __init__(self):
        self.username = None
        self.role = None
        self.token = None
        self.history = []
        self.copied_text_history = []
        self.ws = None
        self.last_clipboard_text = None
        self.monitoring = False

    def on_message(self, ws, message):
        data = json.loads(message)
        if data["type"] == "copy":
            pyperclip.copy(data["text"])
            print(f"Received and copied to clipboard: {data['text']}")

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")

    def on_open(self, ws):
        print("WebSocket connection opened")

    def start_websocket(self):
        ws_url = f"wss://clipboard-a6qozbmi4-abhishek-sharmas-projects-2069d670.vercel.app/ws/{self.username}?token={self.token}"
        self.ws = websocket.WebSocketApp(ws_url,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    def authenticate(self):
        print("\n=== Login ===")
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()
        if not username or not password:
            print("Error: Username and password cannot be empty.")
            return False
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/authenticate",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            if data["status"] == "success":
                self.username = data["username"]
                self.role = data["role"]
                self.token = data["token"]
                self.start_websocket()
                monitor_thread = threading.Thread(target=self.start_clipboard_monitoring)
                monitor_thread.daemon = True
                monitor_thread.start()
                print(f"\nWelcome, {self.username}! (Role: {self.role})")
                return True
            else:
                print(f"Error: {data['message']}")
                return False
        except requests.RequestException as e:
            print(f"Error: Failed to connect to server: {e}")
            return False

    def start_clipboard_monitoring(self):
        self.monitoring = True
        print("Starting clipboard monitoring...")
        while self.monitoring:
            try:
                current_text = pyperclip.paste()
                if current_text != self.last_clipboard_text and current_text.strip():
                    print(f"Detected new clipboard text: {current_text}")
                    self.last_clipboard_text = current_text
                    response = requests.post(
                        f"{API_BASE_URL}/api/submit_copied_text/{self.username}",
                        json={"text": current_text},
                        headers={"Authorization": f"Bearer {self.token}"}
                    )
                    response.raise_for_status()
                    data = response.json()
                    if data["status"] == "success":
                        print("Copied text sent to server!")
                        self.load_clipboard_data()
            except Exception as e:
                print(f"Error monitoring clipboard: {e}")
            time.sleep(1)

    def stop_clipboard_monitoring(self):
        self.monitoring = False
        print("Stopped clipboard monitoring.")

    def load_clipboard_data(self):
        if not self.username:
            print("Error: Not logged in.")
            return False
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/history/{self.username}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
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
                json={"text": text},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            response.raise_for_status()
            data = response.json()
            if data["status"] == "success":
                print("Text submitted successfully!")
                self.load_clipboard_data()
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
                self.stop_clipboard_monitoring()
                print(f"Goodbye, {self.username}!")
                self.username = None
                self.role = None
                self.token = None
                self.history = []
                self.copied_text_history = []
                return True
            elif choice == "9":
                self.stop_clipboard_monitoring()
                print("Exiting Clipboard Manager. Goodbye!")
                return False
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
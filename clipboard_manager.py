import requests
import pyperclip

# Configuration
API_BASE_URL = "https://clipboard-ihpifoma4-abhishek-sharmas-projects-2069d670.vercel.app"

class ClipboardManager:
    def __init__(self):
        self.username = None
        self.role = None
        self.history = []
        self.copied_text_history = []

    def authenticate(self):
        print("\n=== Login ===")
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()

        if not username or not password:
            print("Error: Username and password cannot be empty.")
            return False

        # Make API request to authenticate
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/authenticate",
                data={"username": username, "password": password}
            )
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

    def main_menu(self):
        while True:
            print("\n=== Clipboard Manager ===")
            print(f"Logged in as: {self.username} ({self.role})")
            print("1. View History")
            print("2. View Copied Text History")
            print("3. Copy from History")
            print("4. Copy from Copied Text History")
            print("5. Refresh Data")
            print("6. Logout")
            print("7. Exit")

            choice = input("Enter your choice (1-7): ").strip()

            if choice == "1":
                self.display_history("history")
            elif choice == "2":
                self.display_history("copied_text_history")
            elif choice == "3":
                self.copy_to_clipboard("history")
            elif choice == "4":
                self.copy_to_clipboard("copied_text_history")
            elif choice == "5":
                if self.load_clipboard_data():
                    print("Data refreshed successfully.")
            elif choice == "6":
                print(f"Goodbye, {self.username}!")
                self.username = None
                self.role = None
                self.history = []
                self.copied_text_history = []
                return True  # Return to login screen
            elif choice == "7":
                print("Exiting Clipboard Manager. Goodbye!")
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
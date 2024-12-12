from datetime import datetime, timedelta
import random

class Authenticator:
    def __init__(self, user_file, password_file):
        self.USER_FILE = user_file
        self.PASSWORD_FILE = password_file

        self.mock_db = {}
        self.login_attempts = {}  # Tracks login attempts: {"username": [{"ip": ..., "timestamp": ...}]}
        self.blocked_users = {}  # Tracks blocked users: {"username": unblock_time}

        self.MAX_ATTEMPTS = 5
        self.BLOCK_DURATION = timedelta(seconds=3)

        # Initialize the mock database
        self.mock_db = self.generate_mock_db()

    def load_data(self):
        """Load data from user and password files."""
        with open(self.USER_FILE, 'r') as uf, open(self.PASSWORD_FILE, 'r') as pf:
            usernames = [line.strip() for line in uf.readlines()]
            passwords = [line.strip() for line in pf.readlines()]
        return usernames, passwords

    def generate_mock_db(self):
        """Generate mock database with 100 username-password pairs."""
        usernames, passwords = self.load_data()
        if len(usernames) < 100 or len(passwords) < 100:
            raise ValueError("Insufficient data in username or password files.")

        selected_users = random.sample(usernames, 100)
        selected_passwords = random.sample(passwords, 100)

        return {user: pwd for user, pwd in zip(selected_users, selected_passwords)}

    def authenticate(self, username, password, ip_address):
        """Authenticate a user and manage login attempts and blocking."""
        current_time = datetime.now()

        # Check if the user is currently blocked
        if username in self.blocked_users:
            unblock_time = self.blocked_users[username]
            if current_time < unblock_time:
                return "error: User is blocked. Try again later.", 403
            else:
                del self.blocked_users[username]  # Unblock the user

        # Record the login attempt
        if username not in self.login_attempts:
            self.login_attempts[username] = []

        # Filter out expired attempts
        self.login_attempts[username] = [
            attempt for attempt in self.login_attempts[username]
            if current_time - attempt['timestamp'] < self.BLOCK_DURATION
        ]

        # Add the current attempt
        self.login_attempts[username].append({"ip": ip_address, "timestamp": current_time})

        # Check if attempts exceed the limit
        if len(self.login_attempts[username]) > self.MAX_ATTEMPTS:
            self.blocked_users[username] = current_time + self.BLOCK_DURATION
            return "error: Too many failed attempts. User is blocked.", 403

        # Check credentials
        if username in self.mock_db and self.mock_db[username] == password:
            return "message: Login successful! username"+ username, 200

        return "error: Invalid username or password.", 401

    def reset_database(self):
        """Reset and regenerate the mock database."""
        self.mock_db = self.generate_mock_db()
        return {"message": "Mock database reset successfully!"}

    def get_credentials(self):
        """Retrieve the current mock database."""
        return self.mock_db

    def status(self):
        """Retrieve the status of login attempts and blocked users."""
        return {"login_attempts": self.login_attempts, "blocked_users": self.blocked_users}

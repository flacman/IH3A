from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# Mock data sources
USER_FILE = "../Data/200-usernames.txt"
PASSWORD_FILE = "../Data/100-passwords.txt"

# In-memory mock database
mock_db = {}

# In-memory data store for simulation
login_attempts = {}  # Tracks login attempts: {"username": [{"ip": ..., "timestamp": ...}]}
blocked_users = {}  # Tracks blocked users: {"username": unblock_time}

MAX_ATTEMPTS = 5
BLOCK_DURATION = timedelta(seconds=3)  # Change the block duration to 3 seconds

# Load data from files
def load_data():
    with open(USER_FILE, 'r') as uf, open(PASSWORD_FILE, 'r') as pf:
        usernames = [line.strip() for line in uf.readlines()]
        passwords = [line.strip() for line in pf.readlines()]
    return usernames, passwords

# Generate mock database with 100 username-password pairs
def generate_mock_db():
    usernames, passwords = load_data()
    if len(usernames) < 100 or len(passwords) < 100:
        raise ValueError("Insufficient data in username or password files.")

    selected_users = random.sample(usernames, 100)
    selected_passwords = random.sample(passwords, 100)

    return {user: pwd for user, pwd in zip(selected_users, selected_passwords)}

@app.route('/credentials', methods=['GET'])
def get_credentials():
    """Endpoint to retrieve the current mock database."""
    return jsonify(mock_db), 200

@app.route('/reset', methods=['POST'])
def reset_database():
    """Endpoint to reset and regenerate the mock database."""
    global mock_db
    mock_db = generate_mock_db()
    return jsonify({"message": "Mock database reset successfully!"}), 200

@app.route('/login', methods=['POST'])
def login():
    """Endpoint for login simulation."""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    ip_address = request.remote_addr

    current_time = datetime.now()

    # Check if the user is currently blocked
    if username in blocked_users:
        unblock_time = blocked_users[username]
        if current_time < unblock_time:
            return jsonify({"error": "User is blocked. Try again later."}), 403
        else:
            del blocked_users[username]  # Unblock the user

    # Record the login attempt
    if username not in login_attempts:
        login_attempts[username] = []

    # Filter out expired attempts
    login_attempts[username] = [
        attempt for attempt in login_attempts[username]
        if current_time - attempt['timestamp'] < BLOCK_DURATION
    ]

    # Add the current attempt
    login_attempts[username].append({"ip": ip_address, "timestamp": current_time})

    # Check if attempts exceed the limit
    if len(login_attempts[username]) > MAX_ATTEMPTS:
        blocked_users[username] = current_time + BLOCK_DURATION
        return jsonify({"error": "Too many failed attempts. User is blocked."}), 403

    # Check credentials
    if username in mock_db and mock_db[username] == password:
        return jsonify({"message": "Login successful!", "username": username}), 200

    return jsonify({"error": "Invalid username or password."}), 401

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    ip_address = data.get('ip', '127.0.0.1')  # Default IP if not provided

    # Mock the request as if it were from a real client
    with app.test_request_context(
        '/login',
        method='POST',
        json={"username": username, "password": password},
        headers={"X-Forwarded-For": ip_address}
    ):
        return login()
    
@app.route('/status', methods=['GET'])
def status():
    """Endpoint to retrieve login attempts and blocked users."""
    return jsonify({"login_attempts": login_attempts, "blocked_users": blocked_users})

if __name__ == '__main__':
    # Initialize the mock database
    mock_db = generate_mock_db()
    app.run(host='0.0.0.0', port=9000, debug=True)

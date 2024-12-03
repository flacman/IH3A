from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# In-memory data store for simulation
users = {
    "test_user": "password123"  # Mock username-password pair
}

login_attempts = {}  # Tracks login attempts: {"username": [{"ip": ..., "timestamp": ...}]}
blocked_users = {}  # Tracks blocked users: {"username": unblock_time}

MAX_ATTEMPTS = 5
BLOCK_DURATION = timedelta(seconds=3)  # Change the block duration to 3 seconds

@app.route('/login', methods=['POST'])
def login():
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
    if username in users and users[username] == password:
        return jsonify({"message": "Login successful!", "token": "mock-jwt-token"})

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
    return jsonify({"login_attempts": login_attempts, "blocked_users": blocked_users})

if __name__ == '__main__':
    app.run(port=9000, debug=True, host='0.0.0.0')

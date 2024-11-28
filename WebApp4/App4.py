from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib
import time

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # Change this to a random secret

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'user2'
app.config['MYSQL_PASSWORD'] = 'password2'
app.config['MYSQL_DB'] = 'database2'

mysql = MySQL(app)
jwt = JWTManager(app)

# Persistent store for blocked users
blocked_users = set()
MAX_BLOCKED_USERS = 50
TOTAL_USERS = 100  # Total number of users in the system

@app.route('/')
def loginForm():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    global blocked_users
    data = request.get_json()
    username = data.get('username', None)
    password = data.get('password', None)

    # Check if the user is already blocked
    if username in blocked_users:
        return jsonify({"msg": "The user is blocked permanently"}), 403

    # Check if more than 50 users are blocked
    if len(blocked_users) > MAX_BLOCKED_USERS:
        return jsonify({"msg": "Too many blocked users, service unavailable"}), 510

    # Check if user exists in the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
    user_exists = cursor.fetchone()

    if not user_exists:
        return jsonify({"msg": "Bad username or password"}), 401

    # Hash the password using SHA1
    password_hash = hashlib.sha1(password.encode()).hexdigest()

    query = 'SELECT * FROM user WHERE username = %s AND password_hash = %s'
    cursor.execute(query, (username, password_hash))
    account = cursor.fetchone()

    if account:
        return jsonify(access_token=create_access_token(identity=username))
    else:
        # Increment failed login attempts
        cursor.execute('SELECT failed_attempts FROM user WHERE username = %s', (username,))
        attempts = cursor.fetchone()['failed_attempts']
        
        # Block the user if attempts reach 3
        if attempts + 1 >= 3:
            blocked_users.add(username)
            cursor.execute('UPDATE user SET failed_attempts = 3 WHERE username = %s', (username,))
            mysql.connection.commit()
            return jsonify({"msg": "The user is blocked permanently"}), 403

        # Increment failed attempts
        cursor.execute('UPDATE user SET failed_attempts = failed_attempts + 1 WHERE username = %s', (username,))
        mysql.connection.commit()

        return jsonify({"msg": "Bad username or password"}), 401

@app.route('/welcome', methods=['GET'])
def welcome():
    return render_template('welcome.html')

@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(redirect(url_for('loginForm')))
    unset_jwt_cookies(response)
    return response

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

if __name__ == '__main__':
    app.run(port=8084, debug=True, host='0.0.0.0')

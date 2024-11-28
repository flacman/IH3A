from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, verify_jwt_in_request, get_jwt_identity, unset_jwt_cookies
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

# In-memory cache to track login attempts per session
session_login_attempts = {}

@app.route('/')
def loginForm():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', None)
    password = data.get('password', None)
    client_ip = request.remote_addr

    session_key = f"{client_ip}:{username}"

    # Check if user exists in the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
    user_exists = cursor.fetchone()
    
    if not user_exists:
        return jsonify({"msg": "Bad username or password"}), 401

    # Check if the user is blocked for this session
    if session_key in session_login_attempts:
        attempts, last_attempt_time = session_login_attempts[session_key]
        if attempts >= 5 and time.time() - last_attempt_time < 300:
            return jsonify({"msg": "The user is blocked for this session"}), 403

    # Hash the password using SHA1
    password_hash = hashlib.sha1(password.encode()).hexdigest()

    query = 'SELECT * FROM user WHERE username = %s AND password_hash = %s'
    cursor.execute(query, (username, password_hash))
    account = cursor.fetchone()

    if account:
        # Reset login attempts on successful login
        if session_key in session_login_attempts:
            del session_login_attempts[session_key]
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    else:
        # Track login attempts for the session
        if session_key in session_login_attempts:
            attempts, last_attempt_time = session_login_attempts[session_key]
            session_login_attempts[session_key] = (attempts + 1, time.time())
        else:
            session_login_attempts[session_key] = (1, time.time())
        return jsonify({"msg": "Bad username or password"}), 401

@app.route('/welcome', methods=['GET'])
def welcome():
    verify_jwt_in_request()
    current_user = get_jwt_identity()
    return render_template('welcome.html', username=current_user)

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
    app.run(port=8083, debug=True, host='0.0.0.0')

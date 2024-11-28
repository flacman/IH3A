from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Secure session configuration
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=False,
    SESSION_COOKIE_SAMESITE='Lax'
)
# MySQL configurations

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'user1'
app.config['MYSQL_PASSWORD'] = 'password1'
app.config['MYSQL_DB'] = 'database1'

mysql = MySQL(app)
# Database configuration
db_config = {
    'user': 'app1',
    'password': 'app1',
    'host': 'localhost',
    'database': 'app1'
}

# Connect to the database
def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']
    
    # Hash the password using SHA1
    password_hash = hashlib.sha1(password.encode()).hexdigest()
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check if the user exists
    user_query = 'SELECT * FROM user WHERE username = %s'
    cursor.execute(user_query, (username,))
    user_exists = cursor.fetchone()

    if not user_exists:
        return 'Invalid credentials'

    # Check if the password is correct
    query = 'SELECT * FROM user WHERE username = %s AND password_hash = %s'
    cursor.execute(query, (username, password_hash))
    account = cursor.fetchone()
    loginattempts_key = 'login_attempts' + username
    blocktime_key = 'block_time' + username
    if account:
        session['username'] = username
        session.pop(loginattempts_key, None)  # Reset login attempts on successful login
        session.pop(blocktime_key, None)  # Reset block time on successful login
        return redirect(url_for('welcome'))
    elif user_exists:
        if blocktime_key not in session:
            session[blocktime_key] = time.time()
        elapsed_time = time.time() - session[blocktime_key]
        if elapsed_time > 3:
            session.pop(loginattempts_key, None)
            session[blocktime_key] = time.time()
        
        if loginattempts_key not in session:
            session[loginattempts_key] = 0
        session[loginattempts_key] += 1

        if session[loginattempts_key] >= 5:
            session[blocktime_key] = time.time()  # Reset block time
            print("Blocked!")
            return "errorUser is blocked. Please wait.", 403

    return 'Invalid credentials'

@app.route('/welcome')
def welcome():
    if 'username' in session:
        return render_template('welcome.html', username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(port=8083, debug=True, host='0.0.0.0')
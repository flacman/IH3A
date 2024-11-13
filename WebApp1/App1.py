from flask import Flask, request, render_template, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib

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
    query = 'SELECT * FROM user WHERE username = %s AND password_hash = %s'
    cursor.execute(query, (username, password_hash))
    account = cursor.fetchone()
    #account = False
    #if username == 'adejr12' and password == 'Zbff315':
        #account = True

    if account:
        session['username'] = username
        return redirect(url_for('welcome'))
    else:
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
    app.run(port=8081, debug=True, host='0.0.0.0')
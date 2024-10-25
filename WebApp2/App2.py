from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, verify_jwt_in_request, get_jwt_identity, unset_jwt_cookies
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # Change this to a random secret

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'your_mysql_user'
app.config['MYSQL_PASSWORD'] = 'your_mysql_password'
app.config['MYSQL_DB'] = 'your_database_name'

mysql = MySQL(app)
jwt = JWTManager(app)

@app.route('/')
def loginForm():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', None)
    password = request.form.get('password', None)
    
    # Hash the password using SHA1
    password_hash = hashlib.sha1(password.encode()).hexdigest()
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = 'SELECT * FROM users WHERE username = %s AND password_hash = %s'
    cursor.execute(query, (username, password_hash))
    account = cursor.fetchone()
    
    if account:
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    else:
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
    app.run(debug=True)
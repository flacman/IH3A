from flask import Flask, request, jsonify
import csv
import hashlib
import subprocess

import mysql.connector

app = Flask(__name__)

# Database configurations
db_config_1 = {
    'host': 'localhost',
    'user': 'user1',
    'password': 'password1',
    'database': 'database1'
}

db_config_2 = {
    'host': 'localhost',
    'user': 'user2',
    'password': 'password2',
    'database': 'database2'
}

def connect_to_database(config):
    return mysql.connector.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database']
    )

def clear_user_table(cursor):
    cursor.execute("DELETE FROM user")

def populate_user_table(cursor, csv_file):
    with open(csv_file, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            username, password = row
            password_hash = hashlib.sha1(password.encode()).hexdigest()
            cursor.execute("INSERT INTO user (username, password_hash) VALUES (%s, %s)", (username, password_hash))

@app.route('/restart-database', methods=['POST'])
def restart_database():
    csv_file = request.json.get('csv_file')
    if not csv_file:
        return jsonify({"error": "CSV file path is required"}), 400

    for config in [db_config_1, db_config_2]:
        conn = connect_to_database(config)
        cursor = conn.cursor()
        clear_user_table(cursor)
        populate_user_table(cursor, csv_file)
        conn.commit()
        cursor.close()
        conn.close()

    return jsonify({"message": "Databases restarted successfully"}), 200

@app.route('/restart_apache', methods=['POST'])
def restart_apache():
    try:
        result = subprocess.run(['net', 'stop', 'Apache2.4'], check=True, capture_output=True, text=True)
        result = subprocess.run(['net', 'start', 'Apache2.4'], check=True, capture_output=True, text=True)
        return jsonify({'status': 'success', 'message': 'Apache service restarted successfully.'})
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/full_reset', methods=['POST'])
def full_reset():
    try:
        # Restart databases
        restart_database()
        
        # Restart Apache service
        restart_apache()
        
        return jsonify({'status': 'success', 'message': 'Full reset completed successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
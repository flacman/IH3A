from flask import Flask, request, jsonify
import mysql.connector
import csv
import hashlib
import random
from mysql.connector import pooling

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

# Connection pool configurations
pool_config_1 = {
    'pool_name': 'pool1',
    'pool_size': 5,
    **db_config_1
}

pool_config_2 = {
    'pool_name': 'pool2',
    'pool_size': 5,
    **db_config_2
}

# Create connection pools
pool_1 = pooling.MySQLConnectionPool(**pool_config_1)
pool_2 = pooling.MySQLConnectionPool(**pool_config_2)

# In-memory storage for CSV rows
csv_rows = []

def get_connection(pool):
    return pool.get_connection()

def init_db(pool, config):
    conn = get_connection(pool)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']}")
    cursor.execute(f"USE {config['database']}")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            password_hash CHAR(40) NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def clear_user_table(cursor):
    cursor.execute("DELETE FROM user")

def read_csv_file(csv_file):
    with open(csv_file, 'r') as file:
        reader = csv.reader(file,delimiter=',')
        rows = list(reader)
    return rows

def populate_user_table(cursor, rows):
    random.shuffle(rows)
    selected_rows = rows[:10]  # Select up to 10 random rows
    
    #print out what credentials are used for personal testing
    print("Credentials:\n")
    print(selected_rows)

    for row in selected_rows:
        username, password = row
        password_hash = hashlib.sha1(password.encode()).hexdigest()
        cursor.execute("INSERT INTO user (username, password_hash) VALUES (%s, %s)", (username, password_hash))

@app.route('/restart-database', methods=['GET'])
def restart_database():
    if not csv_rows:
        return jsonify({"error": "CSV data not loaded"}), 500

    for pool, config in [(pool_1, db_config_1), (pool_2, db_config_2)]:
        init_db(pool, config)  # Initialize the database
        conn = get_connection(pool)
        cursor = conn.cursor()
        clear_user_table(cursor)
        populate_user_table(cursor, csv_rows)
        conn.commit()
        cursor.close()
        conn.close()

    return jsonify({"message": "Databases restarted and populated successfully"}), 200

@app.route('/restart-database/<int:pool_number>', methods=['GET'])
def restart_specific_database(pool_number):
    if not csv_rows:
        return jsonify({"error": "CSV data not loaded"}), 500

    if pool_number == 1:
        pool, config = pool_1, db_config_1
    elif pool_number == 2:
        pool, config = pool_2, db_config_2
    else:
        return jsonify({"error": "Invalid pool number"}), 400

    init_db(pool, config)  # Initialize the database
    with pool.get_connection() as conn:
        with conn.cursor() as cursor:
            clear_user_table(cursor)
            populate_user_table(cursor, csv_rows)
            conn.commit()

    return jsonify({"message": "Databases restarted and populated successfully"}), 200

if __name__ == '__main__':
    csv_file_path = 'credentials.csv'  # Update this path to your CSV file
    csv_rows = read_csv_file(csv_file_path)
    app.run(host='0.0.0.0', port=81, debug=True)
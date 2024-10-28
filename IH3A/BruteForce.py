import queue
import threading
from itertools import product
import HTTP  # Assuming HTTP is a module with the make_request function

lock = threading.Lock()
# Event to signal when valid credentials are found
found_event = threading.Event()

users:queue.Queue = queue.Queue()
passwords = []
    #global index to see how many tries have been made
index:int = 0

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

def getPass():
    user = None
    password = None
    #we don't have more users or passwords
    if (passIndex >= passwords.count() or users.Count == 0):
        user= None
        password = None
        return user, password
    
    #get the next password and update the index for the next thread
    password = passwords[passIndex]
    passIndex += 1

    #the last one
    #todo: check if this is correct or it should be passIndex == passwords.count()-1
    if (passIndex == passwords.count()):
    
        passIndex = 0
        user=users.pop()
    else: #replacement for peek
        user = users.pop()
        users.put(user)
    return user, password

#could be used by external functions if there's an error with the actual user and you need to skip to the next one
def tryNextUser():
    passIndex = passwords.count()-1

# Worker function to process the tasks
def worker(users, passwords):
    while(found_event.is_set() == False):
        try:
            lock.acquire()
            user, password = getPass()
            lock.release()
        except queue.Empty:
            break
        finally:
            lock.release()

        if HTTP.make_request(user, password):  # Assuming this function returns True on success
            found_event.set()
            break
        index = index + 1
   
   
#    for user, password in product(users, passwords):
#        if found_event.is_set():
#            break
#        if HTTP.make_request(user, password):  # Assuming this function returns True on success
#            found_event.set()
#            break

# Main function to manage threads
def brute_force(u, p, passwordSpray = False):
    if passwordSpray:
        u, p = p, u
    
    index = 0
    users = queue.Queue()
    for user in u:
        users.put(user)
    passwords = p
    threads = []

    for _ in range(50):  # Adjust the number of threads as needed
        thread = threading.Thread(target=worker, args=(users, passwords))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return found_event.is_set()

# Example usage
if __name__ == "__main__":
    user_file = "users.txt"  # Path to the user list file
    password_file = "passwords.txt"  # Path to the password list file
    delimiter = None  # Set to a delimiter if the user file contains user[delimiter]password pairs

    users, passwords = read_user_list(user_file, delimiter)
    if not passwords:  # If passwords were not read from the user file
        passwords = read_password_list(password_file)
    
    success = brute_force(users, passwords, False)
    if success:
        print("Valid credentials found!")
    else:
        print("No valid credentials found.")
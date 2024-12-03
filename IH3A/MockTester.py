import requests
import time

# URL of the Flask app
BASE_URL = "http://127.0.0.1:9000/simulate"  # Replace with the correct URL if needed

# Mock user credentials
username = "test_user"
wrong_password = "wrongpassword"  # Intentionally incorrect password

# IP addresses to test
ip_addresses = ["127.0.0.1", "169.233.154.8"]  # List of IPs to simulate requests from

# Simulate failed login attempts from different IPs
def simulate_failed_attempts_from_ips():
    for ip in ip_addresses:
        print(f"\nSimulating failed login attempts from IP: {ip}")
        
        # Try 3 failed login attempts from each IP address
        for attempt in range(1, 4):
            ip = ip_addresses[attempt % 2]  # Alternate IP address (127.0.0.1, 169.233.154.8)
            print(f"Attempt {attempt} from IP {ip}...")
            response = requests.post(
                BASE_URL, 
                json={"username": username, "password": wrong_password}, 
                headers={"X-Forwarded-For": ip}  # Simulate different IP using the header
            )
            
            if response.status_code == 403:
                print(f"User is blocked from IP {ip}. Try again later.")
                break
            else:
                print(f"Response: {response.json()}")
            
            time.sleep(1)  # Adding a small delay between attempts to avoid too fast requests

# Simulate login attempt from an IP after blocking time expires
def simulate_valid_attempt_after_block():
    # Wait for 6 seconds (simulating waiting for the block to expire)
    print("Waiting for block to expire...")
    time.sleep(0)

    print("Attempting login after block period...")
    # Now try a valid login from the first IP (127.0.0.1)
    response = requests.post(
        BASE_URL, 
        json={"username": username, "password": "password123"},  # Correct password
        headers={"X-Forwarded-For": "127.0.0.1"}  # Using 127.0.0.1 as the IP after the block period
    )

    if response.status_code == 200:
        print(f"Login successful: {response.json()}")
    else:
        print(f"Login failed: {response.json()}")

if __name__ == "__main__":
    # Simulate 3 failed login attempts from each IP
    simulate_failed_attempts_from_ips()

    # Simulate a valid login attempt after the block time (optional)
    simulate_valid_attempt_after_block()

import socket
import sys

def create_socket(source_ip):
    try:
        # Create a socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Bind the socket to the source IP address
        s.bind((source_ip, 0))
        
        return s
    except socket.error as err:
        print(f"Socket creation failed with error {err}")
        sys.exit()

def send_post_request(source_ip, target_ip, target_port, path, data):
    s = create_socket(source_ip)
    
    try:
        # Connect to the target server
        s.connect((target_ip, target_port))
        
        # Create the POST request
        request = f"POST {path} HTTP/1.1\r\n"
        request += f"Host: {target_ip}\r\n"
        request += "Content-Type: application/x-www-form-urlencoded\r\n"
        request += f"Content-Length: {len(data)}\r\n"
        request += "Connection: close\r\n\r\n"
        request += data
        
        # Send the POST request
        s.sendall(request.encode())
        
        # Receive the response
        response = s.recv(4096)
        print(response.decode())
        
    except socket.error as err:
        print(f"Socket error: {err}")
    finally:
        s.close()

if __name__ == "__main__":
    source_ip = "192.168.16.1"  # Change this to your desired source IP address
    target_ip = "192.168.16.146"  # Example target IP (example.com)
    target_port = 8081
    path = "/post"
    data = "key1=value1&key2=value2"
    
    send_post_request(source_ip, target_ip, target_port, path, data)
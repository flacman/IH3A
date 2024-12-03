from Authenticator import Authenticator
import time

# Initialize the Authenticator class
authenticator = Authenticator(user_file="../Data/200-usernames.txt", password_file="../Data/100-passwords.txt")

# Example of authenticating a user
for i in range(7):
    response, status_code = authenticator.authenticate('example_user', 'example_password', '127.0.0.1')
    print(response, status_code)

time.sleep(3)
response, status_code = authenticator.authenticate('example_user', 'example_password', '127.0.0.1')
print(response, status_code)

# Example of checking the current status
print(authenticator.status())

# Example of resetting the mock database
print(authenticator.reset_database())

# # Example of retrieving credentials
# print(authenticator.get_credentials())

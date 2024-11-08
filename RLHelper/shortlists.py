#takes the credentials.csv file, which has 100 valid username and password pairs, and writes them to two text files, each with the list of 100 valid usernames and passwords
import csv

# Open the CSV file
with open("credentials.csv", "r") as csvfile:
    reader = csv.reader(csvfile)
    
    # Lists to store usernames and passwords
    usernames = []
    passwords = []
    
    # Loop through each row in the CSV
    for row in reader:
        usernames.append(row[0])  # Username in the first column
        passwords.append(row[1])  # Password in the second column

# Write usernames to usernames.txt
with open("../Data/100-usernames.txt", "w") as user_file:
    for username in usernames:
        user_file.write(username + "\n")

# Write passwords to passwords.txt
with open("../Data/100-passwords.txt", "w") as pass_file:
    for password in passwords:
        pass_file.write(password + "\n")

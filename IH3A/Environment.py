import tensorflow as tf
import numpy as np
import time
from itertools import cycle
from ..RLHelper.SharedMemLib import read_write_sharedMem
from HTTP import HTTPQuery
from keras.api.models import Sequential
from keras.api.layers import Dense
from keras.api.optimizers import Adam
import socket
import random

class CustomEnv:
    def __init__(self):
        self.state = self.default_state()
        self.query_count = 0
        self.plan = "bruteForce"
        self.users = cycle(["user1", "user2", "user3"])
        self.passwords = cycle(["pass1", "pass2", "pass3"]) 
        self.current_user = next(self.users)
        self.current_password = next(self.passwords)
        self.http_query = HTTPQuery(
            host="http://app1.com",
            default_headers={"Content-Type": "application/x-www-form-urlencoded"},
            post_query="username=${USER}&password=${PASS}",
            path="/login",
            use_post=True,
            use_json=False
        )

    def default_state(self):
        # Define the default state structure
        return np.zeros((1, 10))

    def step(self, action):
        reward = 0
        
        # Define actions
        if action == 0:
            # Thread wait x seconds
            wait_time = 1  # Define wait time in seconds
            time.sleep(wait_time)
        elif action == 1:
            # Skip user
            self.current_user = next(self.users)
        elif action == 2:
            # Try next password
            self.current_password = next(self.passwords)
            query_result = self.http_query.perform_query(
                username=self.current_user,
                password=self.current_password,
                search_string="Welcome"
            )
            self.query_count += 1
            if query_result:
                reward += 10
            else:
                # Call perform_query on SyslogServer.py and check if it returns False
                syslog_result = read_write_sharedMem()
                if not syslog_result:
                    reward += 1
            if self.query_count % 50 == 0:
                reward += 5
        elif action == 3:
            # Stop the process for x seconds
            stop_time = 5  # Define stop time in seconds
            time.sleep(stop_time)
        elif action == 4:
            # Change between planBruteForce and passwordSpray
            self.plan = "passwordSpray" if self.plan == "bruteForce" else "bruteForce"
        elif action == 5:
            # Change IP address from a pool of IPs. This will just work on Windows machines
            ip_pool = cycle(['192.168.0.1', '192.168.0.2', '192.168.0.3', '192.168.0.4'])
            new_ip = next(ip_pool)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((new_ip, 0))
            s.connect(('10.0.0.122', 80))
        else:            
            pass

        # Call read_write_sharedMem and adjust reward if needed
        syslog_output = read_write_sharedMem()
        if syslog_output:
            reward -= 10

        # Return the default state, reward, and done flag
        done = False  # Adjust if the environment has a terminal condition
        return self.state, reward, done

    def reset(self):
        self.state = self.default_state()
        self.query_count = 0
        self.plan = "bruteForce"
        self.current_user = next(self.users)
        self.current_password = next(self.passwords)
        return self.state

class Agent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = []
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.learning_rate = 0.001
        self.model = self._build_model()

    def _build_model(self):
        model = Sequential()
        model.add(Dense(24, input_dim=self.state_size, activation='relu'))
        model.add(Dense(24, activation='relu'))
        model.add(Dense(self.action_size, activation='linear'))
        model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
        return model

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state)
        return np.argmax(act_values[0])

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                target = (reward + self.gamma * np.amax(self.model.predict(next_state)[0]))
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

if __name__ == "__main__":
    env = CustomEnv()
    state_size = 10  # Adjusted to match the default state size in CustomEnv
    action_size = 5
    agent = Agent(state_size, action_size)
    episodes = 1000
    batch_size = 32

    for e in range(episodes):
        state = env.reset()
        for time in range(500):
            action = agent.act(state)
            next_state, reward, done = env.step(action)
            agent.remember(state, action, reward, next_state, done)
            state = next_state
            if done:
                print(f"episode: {e}/{episodes}, score: {time}, e: {agent.epsilon:.2}")
                break
            if len(agent.memory) > batch_size:
                agent.replay(batch_size)
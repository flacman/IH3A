from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import StopTrainingOnRewardThreshold, CallbackList, EvalCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.policies import MultiInputActorCriticPolicy
from stable_baselines3.common.env_util import make_vec_env
import gymnasium
from HTTP import HTTPQuery
import numpy as np
import torch
import torch.nn as nn
from stable_baselines3.common.env_checker import check_env
from gymnasium.envs.registration import register

class CustomMultiInputPolicy(MultiInputActorCriticPolicy):
    def __init__(self, *args, **kwargs):
        super(CustomMultiInputPolicy, self).__init__(*args, **kwargs)
        self.bias_action = 2  # Action to prioritize
        self.num_attempts = 0  # List to keep track of the last two actions

    def forward(self, obs, deterministic=False):
        features = self.extract_features(obs)
        latent_pi, latent_vf = self.mlp_extractor(features)
        distribution = self._get_action_dist_from_latent(latent_pi)
        actions = distribution.get_actions(deterministic=deterministic)
        
        # Bias the action selection towards the desired action
        if not deterministic:
            actions = self.bias_action_selection(actions, distribution)
        
        values = self.value_net(latent_vf)
        log_prob = distribution.log_prob(actions)
        return actions, values, log_prob

    def bias_action_selection(self, actions, distribution):
        # Implement the logic to bias the action selection
        # For example, increase the probability of selecting the desired action
        
        #if len(self.last_actions) >= 4 and self.last_actions[-1] != self.bias_action and self.last_actions[-4] != self.bias_action:
        if self.num_attempts > 4:
            biased_actions = torch.full_like(actions, self.bias_action)
        else:
            biased_actions = actions.clone()
            probabilities = distribution.distribution.probs
            probabilities[:, self.bias_action] += 0.6  # Increase the probability of action 2
            probabilities = probabilities / probabilities.sum(dim=1, keepdim=True)  # Normalize
            biased_actions = torch.multinomial(probabilities, 1).squeeze(1)
        
        # Update the last actions
        #self.last_actions.append(biased_actions.item())
        #if len(self.last_actions) > 4:
        #    self.last_actions.pop(0)
        
        # Reset the counter if action 2 is selected
        if (biased_actions == self.bias_action).any():
            #self.last_actions = []
            self.num_attempts = 0
        else:
            self.num_attempts += 1
        return biased_actions


num_episodes = 10000
max_steps_per_episode = 1000
total_rewards = []
user_file = "../Data/usernames.txt"
password_file = "../Data/passwords.txt"
delimiter = None
best_reward = -np.inf

# Debug flag
debug_mode = False

# Create the HTTPQuery object
http_query_APP2 = HTTPQuery(
    host="http://192.168.16.147:8082",
    path="/login",
    use_post=True,
    use_json=True
)

# Register the custom environment
register(
    id='BruteForceEnv-v0',
    entry_point='BF_GymEnv:BruteForceEnv',
    max_episode_steps=max_steps_per_episode,
    kwargs={'user_file': user_file, 'password_file': password_file, 'delimiter': None, 'http_query': http_query_APP2}
)

# Function to create the environment
def make_env():
    if debug_mode:
         return gymnasium.make('BruteForceEnv-v0')
    else:
        return make_vec_env('BruteForceEnv-v0', n_envs=10, seed=0,env_kwargs={'user_file': user_file, 'password_file': password_file, 'max_num_steps':max_steps_per_episode,'delimiter': None, 'http_query': http_query_APP2})
    

if __name__ == "__main__":
    
    # Single-threaded environment for debugging
    env = make_env().unwrapped
    #else:
        # Multi-threaded environment with 10 parallel environments
    #    gymnasium.make_vec_env('BruteForceEnv-v0', n_envs=10, seed=0)
    #    env_fns = [lambda: make_env() for _ in range(10)]
    #    env = gymnasium.vector.SyncVectorEnv(env_fns)

    #check_env(env, warn=True, skip_render_check=True)

    # Create the callbacks
    eval_callback = EvalCallback(env, best_model_save_path='./logs/',
                                 log_path='./logs/', eval_freq=500,
                                 deterministic=True, render=False)
    #callback_on_best = StopTrainingOnRewardThreshold(reward_threshold=500, verbose=1)
    
    callback = CallbackList([eval_callback])

    # Create the PPO model
    #model = PPO("MultiInputPolicy", env, verbose=1, tensorboard_log="./ppo_bruteforce_tensorboard/")
    model = PPO(CustomMultiInputPolicy, env, verbose=1, tensorboard_log="./ppo_bruteforce_tensorboard/")
    

    # Train the model with the callback
    model.learn(total_timesteps=max_steps_per_episode * num_episodes, callback=callback)

    # Save the initial model
    model.save("ppo_bruteforce_initial")

    # To load the model later
    # model = PPO.load("ppo_bruteforce")

    # Test the trained model
    for episode in range(num_episodes):
        obs = env.reset()
        episode_reward = 0
        for step in range(max_steps_per_episode):
            action, _states = model.predict(obs)
            obs, rewards, dones, info = env.step(action)
            episode_reward += rewards
            if dones:
                break
        total_rewards.append(episode_reward)
        
        if episode_reward > best_reward:
            best_reward = episode_reward
            model.save(f"ppo_bruteforce_best_episode_{episode + 1}")
        
        print(f"Episode {episode + 1} reward: {episode_reward}")

    # Post-training summary
    print("\n=== Training Complete ===")
    print(f"Average reward per episode: {np.mean(total_rewards):.2f}")
    print(f"Highest reward in an episode: {max(total_rewards)}")
    print(f"Lowest reward in an episode: {min(total_rewards)}")
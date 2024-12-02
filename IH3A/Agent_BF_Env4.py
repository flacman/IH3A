import random
from stable_baselines3 import PPO, A2C
from stable_baselines3.common.callbacks import StopTrainingOnRewardThreshold, CallbackList, EvalCallback, BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.policies import MultiInputActorCriticPolicy
from stable_baselines3.common.env_util import *
import gymnasium
import numpy as np
import torch
import torch.nn as nn
from stable_baselines3.common.env_checker import check_env
from gymnasium.envs.registration import register
from multiprocessing import Process, Manager


#Steps must be longer to get blocked users
#For training use only the 100 passwords
#Rewards on successfull login and list exhausted greately increased
#reward for blocked user is slightly decreased

class CustomMultiInputPolicy(MultiInputActorCriticPolicy):
    def __init__(self, *args, bias_action=2, force_after_n_actions=5, **kwargs):
        super(CustomMultiInputPolicy, self).__init__(*args, **kwargs)
        self.bias_action = bias_action  # Action to prioritize
        self.force_after_n_actions = force_after_n_actions  # Number of actions after which to force the bias action
        self.last_actions = []  # List to keep track of the last actions

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
        if len(self.last_actions) >= self.force_after_n_actions:
            biased_actions = torch.full_like(actions, self.bias_action)
        else:
            biased_actions = actions.clone()
            probabilities = distribution.distribution.probs
            probabilities[:, self.bias_action] += 0.6  # Increase the probability of action 2

            # Ensure actions 0 and 4 are not picked twice in 3 different steps
            for i in range(probabilities.shape[0]):
                if self.last_actions.count(4) >=2:#+ self.last_actions.count(0) >= 2:
                    #probabilities[i, 0] = 0
                    probabilities[i, 4] = 0

            probabilities = probabilities / probabilities.sum(dim=1, keepdim=True)  # Normalize
            biased_actions = torch.multinomial(probabilities, 1).squeeze(1)

        if len(self.last_actions) >= self.force_after_n_actions:# and all(action != self.bias_action for action in self.last_actions[-self.force_after_n_actions:]):
            biased_actions = torch.full_like(actions, self.bias_action)
        else:
            biased_actions = actions.clone()
            probabilities = distribution.distribution.probs
            probabilities[:, self.bias_action] += 0.6  # Increase the probability of action 2
            probabilities = probabilities / probabilities.sum(dim=1, keepdim=True)  # Normalize
            biased_actions = torch.multinomial(probabilities, 1).squeeze(1)
        
        

        # Update the last actions
        self.last_actions.extend(biased_actions.tolist())
        if len(self.last_actions) > self.force_after_n_actions:
            self.last_actions = self.last_actions[-self.force_after_n_actions:]
        
        # Reset the counter if action 2 is selected
        if (biased_actions == self.bias_action).any():
            self.last_actions = []

        return biased_actions

class TensorboardCallback(BaseCallback):
    """
    Custom callback for plotting additional values in tensorboard.
    """

    def __init__(self, verbose=0):
        super(TensorboardCallback, self).__init__(verbose)

    def _on_step(self) -> bool:
        # Log custom metrics
        if 'rewards' in self.locals:
            self.logger.record('custom/episode_reward', self.locals['rewards'])
        try:
            if self.training_env.get_attr('state'):
                self.logger.record('custom/total_time', self.training_env.get_attr('state')[0]['total_time'])
                self.logger.record('custom/total_locks', self.training_env.get_attr('state')[0]['total_locks'])
                self.logger.record('custom/num_attempts', self.training_env.get_attr('state')[0]['num_attempts'])
        except Exception as e:
            pass
        return True
    def _on_rollout_end(self) -> None:
        # Log episode reward at the end of each rollout
        if 'episode_rewards' in self.locals:
            episode_rewards = np.array(self.locals['episode_rewards'])
            self.logger.record('custom/episode_reward', np.sum(episode_rewards))

class IH3Agent:    
    total_rewards = []
    user_file = "../Data/200-usernames.txt"
    password_file = "../Data/100-passwords.txt"
    delimiter = None
    best_reward = -np.inf
    users = []
    passwords = []
    indexPass_map = {}

    # Debug flag
    debug_mode = False

    register(
        id='BruteForceEnvFTP-v0',
        entry_point='BF_GymEnvFTP:BruteForceEnvFTP',
        max_episode_steps=5000,
        kwargs={'users': users, 'passwords': passwords, 'indexPass_map': indexPass_map, 'ftp_query': None, 'agentId':1}
    )
    def __init__(self):
        manager = Manager()
        self.users = manager.list()
        self.passwords = manager.list()
        self.indexPass_map = manager.dict()
        self.read_user_list(self.user_file, None)
        if not self.passwords:
            self.read_password_list(self.password_file)

        self.indexPass_map = {i: 0 for i in range(len(self.users))}
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
        random.shuffle(self.users)
        return self.users, self.passwords

    # Function to read password list from a file
    def read_password_list(self,file_path):

        with open(file_path, 'r') as file:
            for line in file:
                self.passwords.append(line.strip())
        return self.passwords

    def make_env(self):
        
        if self.debug_mode:
            return gymnasium.make('BruteForceEnvFTP-v0', kwargs={'users': agent.users, 'passwords': agent.passwords, 'indexPass_map': agent.indexPass_map, 'ftp_query': None, 'agentId':1})
        else:
            return make_vec_env('BruteForceEnvFTP-v0', n_envs=2, seed=0,env_kwargs={'users': agent.users, 'passwords': agent.passwords, 'indexPass_map': agent.indexPass_map, 'ftp_query': None, 'agentId':1})


num_episodes = 10000
max_steps_per_episode = 5000
#max_steps_per_episode = 1000


if __name__ == "__main__":

    print("CUDA available:", torch.cuda.is_available())
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu") 
    #device = torch.device("cpu") 
    print("Using device:", device)
    
    agent = IH3Agent()
        # Single-threaded environment for debugging
    env = agent.make_env().unwrapped



    #else:
        # Multi-threaded environment with 10 parallel environments
    #    gymnasium.make_vec_env('BruteForceEnv-v0', n_envs=10, seed=0)
    #    env_fns = [lambda: make_env() for _ in range(10)]
    #    env = gymnasium.vector.SyncVectorEnv(env_fns)

    #check_env(env, warn=True, skip_render_check=True)

    # Create the callbacks
    eval_callback = EvalCallback(env, best_model_save_path='./logs/',
                                 log_path='./logs/', eval_freq=1000,
                                 deterministic=True, render=False)
    #callback_on_best = StopTrainingOnRewardThreshold(reward_threshold=500, verbose=1)
    tCallback = TensorboardCallback()
    callback = CallbackList([eval_callback, tCallback])

    # Create the PPO model
    #model = PPO(CustomMultiInputPolicy, env, verbose=1, tensorboard_log="./ppo_bruteforce_tensorboard/")
    model = A2C(CustomMultiInputPolicy, env, verbose=1, tensorboard_log="./ppo_bruteforce_tensorboard/")
    

    # Train the model with the callback
    model.learn(total_timesteps=max_steps_per_episode * num_episodes, callback=callback)

    # Save the initial model
    model.save("A2C_bruteforce_initial")

    # To load the model later
    # model = PPO.load("ppo_bruteforce")
    total_rewards = []
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
            model.save(f"sac_bruteforce_best_episode_{episode + 1}")
        
        print(f"Episode {episode + 1} reward: {episode_reward}")

    # Post-training summary
    print("\n=== Training Complete ===")
    print(f"Average reward per episode: {np.mean(total_rewards):.2f}")
    print(f"Highest reward in an episode: {max(total_rewards)}")
    print(f"Lowest reward in an episode: {min(total_rewards)}")
"""
Multi-Environment Training Script for Your Custom Environment

This script uses your existing Environment class with custom observations and rewards,
but adds multi-environment parallel training for faster learning.
"""

import os
import sys
import numpy as np
import torch
from datetime import datetime
from typing import Dict, List, Tuple
import argparse
import json
from collections import defaultdict, deque
import matplotlib.pyplot as plt
from torch.utils.tensorboard import SummaryWriter

# Import the custom environment wrapper
from custom_env_wrapper import CustomEnvWrapper, MultiEnvWrapper, make_custom_env
from agent_stable_pytorch_corrected import StableCoDQLAgentPyTorch


class CustomMultiEnvTrainer:
    """
    Multi-environment trainer for your custom environment.
    """
    
    def __init__(self, config: Dict):
        """Initialize multi-environment trainer with your custom environment."""
        self.config = config
        
        # Set device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        
        # Create environments
        self.num_envs = config.get('num_parallel_envs', 4)
        print(f"Creating {self.num_envs} parallel custom environments...")
        
        # Create environment factory functions
        env_fns = [
            lambda: make_custom_env(config['env_config'])
            for _ in range(self.num_envs)
        ]
        
        # Create multi-environment wrapper
        self.multi_env = MultiEnvWrapper(env_fns, num_envs=self.num_envs)
        
        # Get agent information
        self.agent_ids = self.multi_env.agents
        self.num_agents = self.multi_env.num_agents
        
        # Determine actual state dimension for each agent
        print("Checking actual observation dimensions...")
        test_obs_list, _ = self.multi_env.reset()
        
        # Get dimensions for each agent
        self.agent_state_dims = {}
        for agent_id in self.agent_ids:
            # Check first environment's observation for this agent
            actual_obs = test_obs_list[0][agent_id]
            self.agent_state_dims[agent_id] = len(actual_obs)
            # print(f"Agent {agent_id} state dim: {len(actual_obs)}")

        first_agent = self.agent_ids[0]
        self.state_dim = self.agent_state_dims[first_agent] # Keep for reference/logging
        
        # Get action dimension
        # Assuming action dimension might also vary? (Usually handled, but good to check)
        
        print(f"State dimensions: {self.agent_state_dims}")
        # print(f"Action dimension: {self.action_dim}") # Calculated inside loop now
        print(f"Number of agents: {self.num_agents}")
        print(f"Agent IDs: {self.agent_ids}")
        
        # Create stable Co-DQL agents (shared across all environments)
        print(f"Creating {self.num_agents} stable Co-DQL agents...")
        self.agents: Dict[str, StableCoDQLAgentPyTorch] = {}
        
        for agent_id in self.agent_ids:
            # Get specific action space for this agent
            agent_action_space = self.multi_env.action_spaces[agent_id]
            agent_action_dim = agent_action_space.n if hasattr(agent_action_space, 'n') else len(agent_action_space)
            
            # Get specific state dim for this agent
            agent_state_dim = self.agent_state_dims[agent_id]
            
            agent = StableCoDQLAgentPyTorch(
                state_dim=agent_state_dim,
                action_dim=agent_action_dim,
                num_actions=agent_action_dim,
                learning_rate=config.get('learning_rate', 0.0003),
                gamma=config.get('gamma', 0.99),
                tau=config.get('tau', 0.005),
                buffer_size=config.get('buffer_size', 100000),
                batch_size=config.get('batch_size', 256),
                epsilon=config.get('epsilon', 1.0),
                epsilon_min=config.get('epsilon_min', 0.01),
                epsilon_decay=config.get('epsilon_decay', 0.994),
                reward_scale=config.get('reward_scale', 0.01),
                gradient_clip=config.get('gradient_clip', 10.0),
                update_target_every=config.get('update_target_every', 1000),
                device=self.device
            )
            self.agents[agent_id] = agent
        
        # Setup logging directories
        self.setup_directories()
        
        # TensorBoard writer
        log_dir = os.path.join(
            config.get('log_dir', 'logs_custom_multienv'),
            f"custom_multienv_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        self.summary_writer = SummaryWriter(log_dir)
        
        # Training statistics
        self.best_episode_reward = -float('inf')
        self.episode_rewards_history = []
        self.episode_waiting_times = []
        self.episode_queues = []
        self.eval_rewards_history = []
        
        # Early stopping
        self.patience = config.get('patience', 200)
        self.no_improvement_count = 0
        self.best_eval_reward = -float('inf')
        
        # Loss tracking
        self.loss_history = deque(maxlen=1000)
        
        # Episode counter
        self.total_episodes = 0
        
        print("Custom multi-environment trainer initialized successfully!")
    
    def setup_directories(self):
        """Create necessary directories for saving models and logs."""
        model_dir = self.config.get('model_dir', 'models_custom_multienv')
        log_dir = self.config.get('log_dir', 'logs_custom_multienv')
        os.makedirs(model_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
    
    def compute_mean_actions(self, actions: Dict[str, int]) -> Dict[str, np.ndarray]:
        """
        Compute mean actions for mean field approximation.
        Note: This uses a shared action dimension across all agents.
        """
        # Find the maximum action dimension
        max_action_dim = max(
            self.multi_env.action_spaces[agent_id].n 
            for agent_id in self.agent_ids
        )
        
        action_counts = np.zeros(max_action_dim)
        for agent_id, action in actions.items():
            if action < max_action_dim:
                action_counts[action] += 1
        
        mean_action_dist = action_counts / len(actions)
        
        # Create mean action for each agent based on their action space
        mean_actions = {}
        for agent_id in self.agent_ids:
            agent_action_dim = self.multi_env.action_spaces[agent_id].n
            # Truncate to agent's action space size
            mean_actions[agent_id] = mean_action_dist[:agent_action_dim].astype(np.float32)
            # Renormalize
            if mean_actions[agent_id].sum() > 0:
                mean_actions[agent_id] /= mean_actions[agent_id].sum()
            else:
                mean_actions[agent_id] = np.ones(agent_action_dim, dtype=np.float32) / agent_action_dim
        
        return mean_actions
    
    def train(self):
        """Main training loop with multi-environment support."""
        num_episodes = self.config.get('num_episodes', 2500)
        eval_frequency = self.config.get('eval_frequency', 50)
        save_frequency = self.config.get('save_frequency', 50)
        
        print(f"\n{'='*60}")
        print(f"Starting Multi-Environment Training for {num_episodes} episodes")
        print(f"Using {self.num_envs} parallel environments")
        print(f"{'='*60}\n")
        
        while self.total_episodes < num_episodes:
            # Run parallel episodes
            all_episode_rewards, all_episode_infos = self.run_parallel_episodes()
            
            # Process results from all environments
            for episode_rewards, episode_info in zip(all_episode_rewards, all_episode_infos):
                self.total_episodes += 1
                
                # Compute episode statistics
                total_reward = sum(episode_rewards.values())
                avg_reward = total_reward / len(episode_rewards)
                
                # Store episode statistics
                self.episode_rewards_history.append(avg_reward)
                self.episode_waiting_times.append(episode_info.get('avg_waiting_time', 0))
                self.episode_queues.append(episode_info.get('avg_queue', 0))
                
                # Get agent statistics
                agent_stats = list(self.agents.values())[0].get_stats()
                avg_loss = np.mean([agent.get_stats()['avg_loss'] for agent in self.agents.values()])
                
                # Log to TensorBoard
                self.summary_writer.add_scalar('episode/total_reward', total_reward, self.total_episodes)
                self.summary_writer.add_scalar('episode/avg_reward', avg_reward, self.total_episodes)
                self.summary_writer.add_scalar('episode/avg_waiting_time', 
                                              episode_info.get('avg_waiting_time', 0), self.total_episodes)
                self.summary_writer.add_scalar('episode/avg_queue', 
                                              episode_info.get('avg_queue', 0), self.total_episodes)
                self.summary_writer.add_scalar('training/epsilon', agent_stats['epsilon'], self.total_episodes)
                self.summary_writer.add_scalar('training/avg_loss', avg_loss, self.total_episodes)
                
                # Print progress
                if self.total_episodes % 10 == 0:
                    recent_avg = np.mean(self.episode_rewards_history[-50:]) if len(self.episode_rewards_history) >= 50 else np.mean(self.episode_rewards_history)
                    print(f"\n{'='*60}")
                    print(f"Episode {self.total_episodes}/{num_episodes}")
                    print(f"{'='*60}")
                    print(f"  Avg Reward: {avg_reward:.2f}")
                    print(f"  Total Reward: {total_reward:.2f}")
                    print(f"  Recent 50 Avg: {recent_avg:.2f}")
                    print(f"  Best Episode Reward: {self.best_episode_reward:.2f}")
                    print(f"  Avg Waiting Time: {episode_info.get('avg_waiting_time', 0):.2f}")
                    print(f"  Avg Queue: {episode_info.get('avg_queue', 0):.2f}")
                    print(f"  Epsilon: {agent_stats['epsilon']:.4f}")
                    print(f"  Avg Loss: {avg_loss:.4f}")
                
                # Evaluation
                if self.total_episodes % eval_frequency == 0:
                    eval_results = self.evaluate(num_episodes=5)
                    self.eval_rewards_history.append(eval_results['avg_reward'])
                    
                    print(f"\n{'*'*60}")
                    print(f"  EVALUATION RESULTS (Episode {self.total_episodes})")
                    print(f"{'*'*60}")
                    print(f"  Eval Avg Reward: {eval_results['avg_reward']:.2f}")
                    print(f"  Eval Std Reward: {eval_results['std_reward']:.2f}")
                    print(f"  Eval Avg Waiting Time: {eval_results['avg_waiting_time']:.2f}")
                    print(f"  Eval Avg Queue: {eval_results['avg_queue']:.2f}")
                    print(f"{'*'*60}\n")
                    
                    # Log evaluation results
                    self.summary_writer.add_scalar('eval/avg_reward', eval_results['avg_reward'], self.total_episodes)
                    self.summary_writer.add_scalar('eval/std_reward', eval_results['std_reward'], self.total_episodes)
                    self.summary_writer.add_scalar('eval/avg_waiting_time', 
                                                  eval_results['avg_waiting_time'], self.total_episodes)
                    
                    # Early stopping check
                    if eval_results['avg_reward'] > self.best_eval_reward:
                        self.best_eval_reward = eval_results['avg_reward']
                        self.no_improvement_count = 0
                        self.save_models("best_model")
                        print(f"  ✓ New best model saved! (eval reward: {eval_results['avg_reward']:.2f})")
                    else:
                        self.no_improvement_count += 1
                        print(f"  No improvement for {self.no_improvement_count} evaluations")
                    
                    # Check early stopping
                    if self.no_improvement_count >= self.patience // eval_frequency:
                        print(f"\n{'!'*60}")
                        print(f"  EARLY STOPPING: No improvement for {self.no_improvement_count * eval_frequency} episodes")
                        print(f"  Best eval reward: {self.best_eval_reward:.2f}")
                        print(f"{'!'*60}\n")
                        break
                
                # Save models periodically
                if self.total_episodes % save_frequency == 0:
                    if avg_reward > self.best_episode_reward:
                        self.best_episode_reward = avg_reward
                        self.save_models(f"checkpoint_episode_{self.total_episodes}")
                        print(f"  ✓ Checkpoint saved (episode reward: {avg_reward:.2f})")
                
                if self.total_episodes >= num_episodes:
                    break
            
            if self.total_episodes >= num_episodes or self.no_improvement_count >= self.patience // eval_frequency:
                break
        
        # Final save
        self.save_models("final")
        print("\n" + "="*60)
        print("Training completed!")
        print("="*60)
        
        # Plot training curves
        self.plot_training_curves()
        
        # Close TensorBoard writer
        self.summary_writer.close()
        
        # Close environments
        self.multi_env.close()
    
    def run_parallel_episodes(self) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
        """Run episodes in parallel across all environments."""
        # Reset all environments
        observations_list, _ = self.multi_env.reset()
        
        # Initialize mean actions for each environment
        mean_actions_list = []
        for _ in range(self.num_envs):
            mean_actions = {}
            for agent_id in self.agent_ids:
                agent_action_dim = self.multi_env.action_spaces[agent_id].n
                mean_actions[agent_id] = np.ones(agent_action_dim, dtype=np.float32) / agent_action_dim
            mean_actions_list.append(mean_actions)
        
        # Episode tracking
        episode_rewards_list = [
            {agent_id: 0.0 for agent_id in self.agent_ids}
            for _ in range(self.num_envs)
        ]
        episode_waiting_times_list = [[] for _ in range(self.num_envs)]
        episode_queues_list = [[] for _ in range(self.num_envs)]
        done_list = [False] * self.num_envs
        step_list = [0] * self.num_envs
        
        max_steps = self.config.get('max_steps_per_episode', 1800)
        
        # Run until all environments are done
        while not all(done_list):
            # Select actions for all agents in all environments
            actions_list = []
            
            for env_idx in range(self.num_envs):
                if done_list[env_idx]:
                    actions_list.append(None)
                    continue
                
                observations = observations_list[env_idx]
                mean_actions = mean_actions_list[env_idx]
                
                actions = {}
                for agent_id in self.agent_ids:
                    action = self.agents[agent_id].select_action(
                        state=observations[agent_id],
                        mean_action=mean_actions[agent_id],
                        exploration=True
                    )
                    actions[agent_id] = action
                
                actions_list.append(actions)
            
            # Compute mean actions for each environment
            current_mean_actions_list = [
                self.compute_mean_actions(actions) if actions is not None else None
                for actions in actions_list
            ]
            
            # Execute actions in all environments
            next_observations_list, rewards_list, terminations_list, truncations_list, infos_list = \
                self.multi_env.step([a for a in actions_list if a is not None])
            
            # Process results for each environment
            result_idx = 0
            for env_idx in range(self.num_envs):
                if done_list[env_idx]:
                    continue
                
                observations = observations_list[env_idx]
                actions = actions_list[env_idx]
                next_observations = next_observations_list[result_idx]
                rewards = rewards_list[result_idx]
                terminations = terminations_list[result_idx]
                truncations = truncations_list[result_idx]
                infos = infos_list[result_idx]
                current_mean_actions = current_mean_actions_list[env_idx]
                
                result_idx += 1
                
                # Check if episode is done
                done = any(terminations.values()) or any(truncations.values())
                step_list[env_idx] += 1
                
                if done or step_list[env_idx] >= max_steps:
                    done_list[env_idx] = True
                
                # Store experiences and train
                for agent_id in self.agent_ids:
                    # Get actual reward value
                    reward_value = rewards[agent_id]() if hasattr(rewards[agent_id], '__call__') else rewards[agent_id]
                    
                    # Store experience
                    self.agents[agent_id].store_transition(
                        state=observations[agent_id],
                        action=actions[agent_id],
                        reward=reward_value,
                        next_state=next_observations[agent_id],
                        next_mean_action=current_mean_actions[agent_id]
                    )
                    
                    # Train agent
                    if step_list[env_idx] % self.config.get('train_frequency', 10) == 0:
                        loss = self.agents[agent_id].update()
                        if loss is not None:
                            self.loss_history.append(loss)
                    
                    # Accumulate rewards
                    episode_rewards_list[env_idx][agent_id] += reward_value
                
                # Collect metrics
                if not done_list[env_idx]:
                    for agent_id in self.agent_ids:
                        if agent_id in infos and 'system_metrics' in infos[agent_id]:
                            metrics = infos[agent_id]['system_metrics']
                            episode_waiting_times_list[env_idx].append(metrics.get('avg_waiting_time', 0))
                            episode_queues_list[env_idx].append(metrics.get('avg_queue', 0))
                            break
                
                # Update observations and mean actions
                observations_list[env_idx] = next_observations
                mean_actions_list[env_idx] = current_mean_actions
        
        # Decay epsilon once per parallel batch
        for agent in self.agents.values():
            agent.decay_epsilon()
        
        # Prepare episode info
        all_episode_rewards = episode_rewards_list
        all_episode_infos = [
            {
                'steps': step_list[i],
                'avg_waiting_time': np.mean(episode_waiting_times_list[i]) if episode_waiting_times_list[i] else 0,
                'avg_queue': np.mean(episode_queues_list[i]) if episode_queues_list[i] else 0,
            }
            for i in range(self.num_envs)
        ]
        
        return all_episode_rewards, all_episode_infos
    
    def evaluate(self, num_episodes: int = 10) -> Dict[str, float]:
        """Evaluate trained agents using first environment."""
        eval_env = self.multi_env.envs[0]
        
        total_rewards = []
        total_waiting_times = []
        total_queues = []
        
        for _ in range(num_episodes):
            observations, _ = eval_env.reset()
            
            mean_actions = {}
            for agent_id in self.agent_ids:
                agent_action_dim = self.multi_env.action_spaces[agent_id].n
                mean_actions[agent_id] = np.ones(agent_action_dim, dtype=np.float32) / agent_action_dim
            
            episode_rewards = {agent_id: 0.0 for agent_id in self.agent_ids}
            episode_waiting_times = []
            episode_queues = []
            done = False
            step = 0
            max_steps = self.config.get('max_steps_per_episode', 1800)
            
            while not done and step < max_steps:
                # Select actions (no exploration)
                actions = {}
                for agent_id in self.agent_ids:
                    action = self.agents[agent_id].select_action(
                        state=observations[agent_id],
                        mean_action=mean_actions[agent_id],
                        exploration=False
                    )
                    actions[agent_id] = action
                
                # Compute mean actions
                current_mean_actions = self.compute_mean_actions(actions)
                
                # Execute actions
                next_observations, rewards, terminations, truncations, infos = eval_env.step(actions)
                
                # Check if done
                done = any(terminations.values()) or any(truncations.values())
                
                # Accumulate rewards
                for agent_id in self.agent_ids:
                    reward_value = rewards[agent_id]() if hasattr(rewards[agent_id], '__call__') else rewards[agent_id]
                    episode_rewards[agent_id] += reward_value
                
                # Collect metrics
                for agent_id in self.agent_ids:
                    if agent_id in infos and 'system_metrics' in infos[agent_id]:
                        metrics = infos[agent_id]['system_metrics']
                        episode_waiting_times.append(metrics.get('avg_waiting_time', 0))
                        episode_queues.append(metrics.get('avg_queue', 0))
                        break
                
                observations = next_observations
                mean_actions = current_mean_actions
                step += 1
            
            avg_reward = sum(episode_rewards.values()) / len(episode_rewards)
            total_rewards.append(avg_reward)
            total_waiting_times.append(np.mean(episode_waiting_times) if episode_waiting_times else 0)
            total_queues.append(np.mean(episode_queues) if episode_queues else 0)
        
        return {
            'avg_reward': np.mean(total_rewards),
            'std_reward': np.std(total_rewards),
            'avg_waiting_time': np.mean(total_waiting_times),
            'std_waiting_time': np.std(total_waiting_times),
            'avg_queue': np.mean(total_queues),
            'std_queue': np.std(total_queues),
        }
    
    def save_models(self, checkpoint_name: str):
        """Save all agent models."""
        model_dir = self.config.get('model_dir', 'models_custom_multienv')
        checkpoint_dir = os.path.join(model_dir, checkpoint_name)
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        for agent_id, agent in self.agents.items():
            filepath = os.path.join(checkpoint_dir, f"{agent_id}.pt")
            agent.save(filepath)
        
        # Save configuration
        config_path = os.path.join(checkpoint_dir, 'config.json')
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        # Save training statistics
        stats_path = os.path.join(checkpoint_dir, 'training_stats.json')
        stats = {
            'episode_rewards': self.episode_rewards_history,
            'episode_waiting_times': self.episode_waiting_times,
            'episode_queues': self.episode_queues,
            'eval_rewards': self.eval_rewards_history,
            'best_episode_reward': float(self.best_episode_reward),
            'best_eval_reward': float(self.best_eval_reward),
            'total_episodes': self.total_episodes,
        }
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def load_models(self, checkpoint_name: str):
        """Load all agent models."""
        model_dir = self.config.get('model_dir', 'models_custom_multienv')
        checkpoint_dir = os.path.join(model_dir, checkpoint_name)
        
        for agent_id, agent in self.agents.items():
            filepath = os.path.join(checkpoint_dir, f"{agent_id}.pt")
            if os.path.exists(filepath):
                agent.load(filepath)
        
        print(f"Models loaded from {checkpoint_dir}")
    
    def plot_training_curves(self):
        """Plot training curves."""
        if not self.episode_rewards_history:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Episode rewards
        axes[0, 0].plot(self.episode_rewards_history, alpha=0.6, label='Episode Reward')
        if len(self.episode_rewards_history) > 50:
            moving_avg = np.convolve(self.episode_rewards_history, np.ones(50)/50, mode='valid')
            axes[0, 0].plot(range(49, len(self.episode_rewards_history)), moving_avg, 
                           'r-', linewidth=2, label='Moving Avg (50)')
        axes[0, 0].set_title('Episode Rewards', fontsize=12, fontweight='bold')
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Average Reward')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Evaluation rewards
        if self.eval_rewards_history:
            eval_frequency = self.config.get('eval_frequency', 50)
            eval_episodes = [i * eval_frequency for i in range(len(self.eval_rewards_history))]
            axes[0, 1].plot(eval_episodes, self.eval_rewards_history, 'o-', linewidth=2)
            axes[0, 1].set_title('Evaluation Rewards', fontsize=12, fontweight='bold')
            axes[0, 1].set_xlabel('Episode')
            axes[0, 1].set_ylabel('Average Reward')
            axes[0, 1].grid(True, alpha=0.3)
        
        # Waiting times
        if self.episode_waiting_times:
            axes[1, 0].plot(self.episode_waiting_times, alpha=0.6)
            if len(self.episode_waiting_times) > 50:
                moving_avg = np.convolve(self.episode_waiting_times, np.ones(50)/50, mode='valid')
                axes[1, 0].plot(range(49, len(self.episode_waiting_times)), moving_avg, 'r-', linewidth=2)
            axes[1, 0].set_title('Average Waiting Time', fontsize=12, fontweight='bold')
            axes[1, 0].set_xlabel('Episode')
            axes[1, 0].set_ylabel('Waiting Time')
            axes[1, 0].grid(True, alpha=0.3)
        
        # Queue lengths
        if self.episode_queues:
            axes[1, 1].plot(self.episode_queues, alpha=0.6)
            if len(self.episode_queues) > 50:
                moving_avg = np.convolve(self.episode_queues, np.ones(50)/50, mode='valid')
                axes[1, 1].plot(range(49, len(self.episode_queues)), moving_avg, 'r-', linewidth=2)
            axes[1, 1].set_title('Average Queue Length', fontsize=12, fontweight='bold')
            axes[1, 1].set_xlabel('Episode')
            axes[1, 1].set_ylabel('Queue Length')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        plot_path = os.path.join(self.config.get('log_dir', 'logs_custom_multienv'), 
                                'training_curves.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"\nTraining curves saved to {plot_path}")
        
        plt.close()


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Multi-Environment Co-DQL Training with Custom Environment')
    parser.add_argument('--episodes', type=int, default=2500, help='Number of training episodes')
    parser.add_argument('--num-envs', type=int, default=4, help='Number of parallel environments')
    parser.add_argument('--learning-rate', type=float, default=0.0003, help='Learning rate')
    parser.add_argument('--use-emergency', action='store_true', help='Use emergency vehicles')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    
    args = parser.parse_args()
    
    # Set random seeds
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
    
    # Configuration
    config = {
        # Environment configuration
        'env_config': {
            'use_emergency_vehicles': args.use_emergency,
            'use_gui': False,
        },
        
        # Training configuration
        'num_episodes': args.episodes,
        'num_parallel_envs': args.num_envs,
        'learning_rate': args.learning_rate,
        'gamma': 0.99,
        'epsilon': 1.0,
        'epsilon_min': 0.01,
        'epsilon_decay': 0.985,
        'batch_size': 256,
        'buffer_size': 100000,
        'tau': 0.005,
        'reward_scale': 0.01,
        'gradient_clip': 10.0,
        'update_target_every': 1000,
        'model_dir': 'models_custom_multienv',
        'log_dir': 'logs_custom_multienv',
        'eval_frequency': 50,
        'save_frequency': 50,
        'max_steps_per_episode': 1800,
        'train_frequency': 10,
        'patience': 100,
    }
    
    # Print configuration
    print("\n" + "="*60)
    print("Multi-Environment Co-DQL Training with Custom Environment")
    print("="*60)
    print(f"Episodes: {config['num_episodes']}")
    print(f"Parallel environments: {config['num_parallel_envs']}")
    print(f"Learning rate: {config['learning_rate']}")
    print(f"Emergency vehicles: {args.use_emergency}")
    print(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print("="*60 + "\n")
    
    # Create trainer and start training
    trainer = CustomMultiEnvTrainer(config)
    trainer.train()


if __name__ == '__main__':
    main()

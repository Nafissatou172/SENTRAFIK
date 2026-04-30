"""
Simulation runner for trained Co-DQL agents.

This script loads trained models and runs a simulation with SUMO GUI
to visualize the performance of the traffic signal control system.
"""

import os
import argparse
import numpy as np
import torch
import json
from typing import Dict

# Import project modules
from modules.environment import Environment
from modules.config_loader import get_config
from agent_stable_pytorch_corrected import StableCoDQLAgentPyTorch


def run_simulation(model_dir: str, episodes: int = 1, use_gui: bool = True, use_emergency: bool = True):
    """
    Run simulation with trained agents.
    
    Args:
        model_dir: Directory containing trained models
        episodes: Number of episodes to run
        use_gui: Whether to show SUMO GUI
        use_emergency: Whether to include emergency vehicles
    """
    print(f"Loading models from: {model_dir}")
    print(f"GUI enabled: {use_gui}")
    print(f"Emergency vehicles: {use_emergency}")
    
    # 1. Initialize Environment
    # We use the single environment for testing (not multi-env wrapper)
    env = Environment(
        use_emergency_vehicles=use_emergency,
        use_gui=use_gui
    )
    
    # 2. Determine Dimensions
    print("Initializing agents...")
    agents: Dict[str, StableCoDQLAgentPyTorch] = {}
    
    # Reset to get first observation for dimension check
    observations, _ = env.reset()
    
    # Config for agent initialization (defaults if config.json not found)
    config = {
        'learning_rate': 0.0003,
        'gamma': 0.99,
        'tau': 0.005,
        'buffer_size': 100000,
        'batch_size': 256,
        'epsilon': 0.0,  # No exploration during test
        'epsilon_min': 0.0,
        'epsilon_decay': 1.0,
        'reward_scale': 0.01,
        'gradient_clip': 10.0,
        'update_target_every': 1000,
    }
    
    # Try to load saved config
    config_path = os.path.join(model_dir, 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
            # Update config with saved values (handling potential key mismatches)
            for k, v in saved_config.items():
                if k in config:
                    config[k] = v
            print("Loaded configuration from checkpoint")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 3. Initialize Agents and Load Weights
    for agent_id in env.agents:
        # Get specific dimensions for this agent
        agent_obs = observations[agent_id]
        state_dim = len(agent_obs)
        
        action_space = env.action_spaces[agent_id]
        action_dim = action_space.n if hasattr(action_space, 'n') else len(action_space)
        
        # Initialize agent
        agent = StableCoDQLAgentPyTorch(
            state_dim=state_dim,
            action_dim=action_dim,
            num_actions=action_dim,
            learning_rate=config['learning_rate'],
            gamma=config['gamma'],
            tau=config['tau'],
            buffer_size=config['buffer_size'],
            batch_size=config['batch_size'],
            epsilon=0.0,  # Force greedy action selection
            epsilon_min=0.0,
            epsilon_decay=1.0,
            reward_scale=config['reward_scale'],
            gradient_clip=config['gradient_clip'],
            update_target_every=config['update_target_every'],
            device=device
        )
        
        # Load weights
        model_path = os.path.join(model_dir, f"{agent_id}.pt")
        if os.path.exists(model_path):
            agent.load(model_path)
        else:
            print(f"Warning: Model for agent {agent_id} not found at {model_path}, using random weights")
        
        agents[agent_id] = agent
        
    print("Agents initialized and loaded.")
    
    # 4. Run Simulation Loop
    for ep in range(episodes):
        print(f"\nStarting Episode {ep + 1}/{episodes}")
        observations, _ = env.reset()
        terminations = {agent_id: False for agent_id in env.agents}
        truncations = {agent_id: False for agent_id in env.agents}
        total_reward = 0
        step = 0
        
        # Initialize mean actions (if needed by your observation/agent logic)
        # Note: StableCoDQL requires mean_action input derived from neighbors
        # But the agent.select_action method takes mean_action argument.
        # We need to compute it.
        
        mean_actions = {
            agent_id: np.ones(env.action_spaces[agent_id].n, dtype=np.float32) / env.action_spaces[agent_id].n
            for agent_id in env.agents
        }
        
        while not (all(terminations.values()) or all(truncations.values())):
            actions = {}
            current_actions_int = {} # For mean action computation
            
            for agent_id in env.agents:
                if terminations[agent_id] or truncations[agent_id]:
                    continue
                    
                obs = observations[agent_id]
                
                # Select greedy action
                action = agents[agent_id].select_action(
                    state=obs,
                    mean_action=mean_actions[agent_id],
                    exploration=False  # Deterministic (Greedy)
                )
                actions[agent_id] = action
                current_actions_int[agent_id] = action
            
            # Compute new mean actions for next step (MF-MARL approximation)
            # Simple global mean for now (aligned with training script logic)
            # Find max action dim
            max_act_dim = max(env.action_spaces[aid].n for aid in env.agents)
            counts = np.zeros(max_act_dim)
            if current_actions_int:
                for a in current_actions_int.values():
                    if a < max_act_dim:
                        counts[a] += 1
                dist = counts / len(current_actions_int)
                
                # Update mean actions dict
                for agent_id in env.agents:
                    aid_dim = env.action_spaces[agent_id].n
                    mean_actions[agent_id] = dist[:aid_dim].astype(np.float32)
                    if mean_actions[agent_id].sum() > 0:
                        mean_actions[agent_id] /= mean_actions[agent_id].sum()
                    else:
                        mean_actions[agent_id] = np.ones(aid_dim) / aid_dim

            # Step environment
            next_observations, rewards, terminations, truncations, info = env.step(actions)
            
            # Accumulate reward
            step_reward = sum(rewards.values())
            total_reward += step_reward
            
            observations = next_observations
            step += 1
            
            # Optional: Print progress
            if step % 100 == 0:
                print(f"Step {step}, Total Reward: {total_reward:.2f}")
                
        print(f"Episode {ep + 1} Finished. Total Reward: {total_reward:.2f}")
        
    env.close()


def main():
    parser = argparse.ArgumentParser(description="Run simulation with trained Oraban agents")
    parser.add_argument('--model-dir', type=str, default='models_custom_multienv/best_model',
                       help='Path to directory containing trained models')
    parser.add_argument('--episodes', type=int, default=1,
                       help='Number of episodes to run')
    parser.add_argument('--no-gui', action='store_true',
                       help='Disable SUMO GUI')
    parser.add_argument('--no-emergency', action='store_true',
                       help='Disable emergency vehicles')
    
    args = parser.parse_args()
    
    use_gui = not args.no_gui
    use_emergency = not args.no_emergency
    
    if not os.path.exists(args.model_dir):
        print(f"Error: Model directory '{args.model_dir}' not found.")
        return
    
    run_simulation(args.model_dir, args.episodes, use_gui, use_emergency)


if __name__ == "__main__":
    main()

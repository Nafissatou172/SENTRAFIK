"""
Gym Environment Wrapper for Your Custom SUMO-RL Environment
Wraps your existing Environment class to be compatible with the Co-DQL multi-env trainer
"""

import numpy as np
from typing import Dict, Tuple, Any
from modules.logging_config import get_logger

# Get module logger
logger = get_logger("oraban.wrapper")


class CustomEnvWrapper:
    """
    Wrapper for your custom Environment class to make it compatible with multi-env training.
    This wrapper maintains compatibility with your existing observation and reward classes.
    """
    
    def __init__(self, 
                 use_emergency_vehicles: bool = True,
                 use_gui: bool = False):
        """
        Initialize wrapper around your custom environment.
        
        Args:
            use_emergency_vehicles: If True, use route file with emergency vehicles
            use_gui: Whether to use SUMO GUI
        """
        # Import your custom Environment class
        # Assuming it's in modules/environment.py
        from modules.environment import Environment
        
        self.env = Environment(
            use_emergency_vehicles=use_emergency_vehicles,
            use_gui=use_gui
        )
        
        # Get agent information from your environment
        self.agents = self.env.agents
        self.num_agents = self.env.num_agents
        self.observation_spaces = self.env.observation_spaces
        self.action_spaces = self.env.action_spaces
        
        logger.info(f"Initialized custom environment with {self.num_agents} agents: {self.agents}")
    
    def reset(self, seed: int = None) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Reset the environment.
        
        Args:
            seed: Random seed (note: SUMO seed is set in Environment init)
            
        Returns:
            observations: Dictionary of observations for each agent
            infos: Dictionary of info for each agent
        """
        observations, infos = self.env.reset()
        return observations, infos
    
    def step(self, actions: Dict[str, int]) -> Tuple[
        Dict[str, np.ndarray],  # observations
        Dict[str, float],        # rewards
        Dict[str, bool],         # terminations
        Dict[str, bool],         # truncations
        Dict[str, Any]           # infos
    ]:
        """
        Execute one step in the environment.
        
        Args:
            actions: Dictionary mapping agent_id to action
            
        Returns:
            observations: Next observations for each agent
            rewards: Rewards for each agent
            terminations: Whether each agent is terminated
            truncations: Whether each agent is truncated
            infos: Additional information
        """
        observations, rewards, terminations, truncations, infos = self.env.step(actions)
        
        # Calculate system-level metrics for monitoring
        system_metrics = self._calculate_system_metrics(infos)
        
        # Add system metrics to each agent's info
        for agent_id in self.agents:
            if agent_id not in infos:
                infos[agent_id] = {}
            infos[agent_id]['system_metrics'] = system_metrics
        
        return observations, rewards, terminations, truncations, infos
    
    def _calculate_system_metrics(self, infos: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate system-level metrics from agent infos.
        
        Args:
            infos: Dictionary of info for each agent
            
        Returns:
            Dictionary of system-level metrics
        """
        # Try to extract metrics from SUMO environment
        try:
            # Get metrics from the underlying SUMO environment
            total_waiting_time = 0
            total_queue = 0
            
            for agent_id in self.agents:
                ts = self.env.env.traffic_signals[agent_id]
                
                # Get waiting time
                waiting_times = ts.get_accumulated_waiting_time_per_lane()
                total_waiting_time += sum(waiting_times)
                
                # Get queue length
                total_queue += ts.get_total_queued()
            
            num_agents = len(self.agents)
            
            return {
                'avg_waiting_time': total_waiting_time / num_agents if num_agents > 0 else 0.0,
                'total_waiting_time': total_waiting_time,
                'avg_queue': total_queue / num_agents if num_agents > 0 else 0.0,
                'total_queue': total_queue,
            }
        except Exception as e:
            # Fallback if metrics unavailable
            return {
                'avg_waiting_time': 0.0,
                'total_waiting_time': 0.0,
                'avg_queue': 0.0,
                'total_queue': 0.0,
            }
    
    def close(self):
        """Close the environment."""
        self.env.close()
    
    @property
    def unwrapped(self):
        """Get the underlying environment."""
        return self.env


class MultiEnvWrapper:
    """
    Wrapper to manage multiple parallel custom environments for faster training.
    """
    
    def __init__(self, env_fns: list, num_envs: int = 4):
        """
        Initialize multiple parallel environments.
        
        Args:
            env_fns: List of functions that create environments
            num_envs: Number of parallel environments
        """
        self.num_envs = num_envs
        self.envs = [env_fn() for env_fn in env_fns[:num_envs]]
        
        # Get agent info from first environment
        self.agents = self.envs[0].agents
        self.num_agents = self.envs[0].num_agents
        self.observation_spaces = self.envs[0].observation_spaces
        self.action_spaces = self.envs[0].action_spaces
        
        logger.info(f"Initialized {num_envs} parallel custom environments")
    
    def reset(self, seed: int = None) -> Tuple[list, list]:
        """
        Reset all environments.
        
        Args:
            seed: Base random seed
            
        Returns:
            List of observations and infos from all environments
        """
        observations_list = []
        infos_list = []
        
        for i, env in enumerate(self.envs):
            env_seed = seed + i if seed is not None else None
            obs, info = env.reset(seed=env_seed)
            observations_list.append(obs)
            infos_list.append(info)
        
        return observations_list, infos_list
    
    def step(self, actions_list: list) -> Tuple[list, list, list, list, list]:
        """
        Execute one step in all environments.
        
        Args:
            actions_list: List of action dictionaries for each environment
            
        Returns:
            Lists of observations, rewards, terminations, truncations, and infos
        """
        observations_list = []
        rewards_list = []
        terminations_list = []
        truncations_list = []
        infos_list = []
        
        for env, actions in zip(self.envs, actions_list):
            obs, rew, term, trunc, info = env.step(actions)
            observations_list.append(obs)
            rewards_list.append(rew)
            terminations_list.append(term)
            truncations_list.append(trunc)
            infos_list.append(info)
        
        return observations_list, rewards_list, terminations_list, truncations_list, infos_list
    
    def close(self):
        """Close all environments."""
        for env in self.envs:
            env.close()


def make_custom_env(config: Dict[str, Any]) -> CustomEnvWrapper:
    """
    Factory function to create your custom environment.
    
    Args:
        config: Configuration dictionary with environment parameters
        
    Returns:
        Wrapped custom environment
    """
    return CustomEnvWrapper(
        use_emergency_vehicles=config.get('use_emergency_vehicles', True),
        use_gui=config.get('use_gui', False)
    )

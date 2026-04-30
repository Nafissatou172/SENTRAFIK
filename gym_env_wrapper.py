"""
Gym Environment Wrapper for SUMO-RL
Wraps sumo-rl to be compatible with the Co-DQL agent
"""

import numpy as np
import gymnasium as gym
from typing import Dict, Tuple, Any
import sumo_rl


class SumoRLWrapper:
    """
    Wrapper for sumo-rl environment to make it compatible with Co-DQL agents.
    Supports both single and parallel environments.
    """
    
    def __init__(self, 
                 net_file: str,
                 route_file: str,
                 use_gui: bool = False,
                 num_seconds: int = 3600,
                 delta_time: int = 5,
                 yellow_time: int = 2,
                 min_green: int = 5,
                 max_green: int = 50,
                 sumo_seed: int = 42,
                 sumo_warnings: bool = False,
                 additional_sumo_cmd: str = None):
        """
        Initialize SUMO-RL environment wrapper.
        
        Args:
            net_file: Path to SUMO network file (.net.xml)
            route_file: Path to SUMO route file (.rou.xml)
            use_gui: Whether to use SUMO GUI
            num_seconds: Simulation duration in seconds
            delta_time: Time between actions in seconds
            yellow_time: Duration of yellow phase
            min_green: Minimum green time
            max_green: Maximum green time
            sumo_seed: Random seed for SUMO
            sumo_warnings: Show SUMO warnings
            additional_sumo_cmd: Additional SUMO command line arguments
        """
        self.env = sumo_rl.parallel_env(
            net_file=net_file,
            route_file=route_file,
            use_gui=use_gui,
            num_seconds=num_seconds,
            delta_time=delta_time,
            yellow_time=yellow_time,
            min_green=min_green,
            max_green=max_green,
            sumo_seed=sumo_seed,
            sumo_warnings=sumo_warnings,
            additional_sumo_cmd=additional_sumo_cmd
        )
        
        # Get agent information after environment is created
        self.agents = None
        self.num_agents = None
        self.observation_spaces = None
        self.action_spaces = None
        
        # Initialize environment to get agent info
        self._initialize_agent_info()
    
    def _initialize_agent_info(self):
        """Initialize agent information from the environment."""
        # Reset to get initial observation
        observations, infos = self.env.reset()
        
        # Get agent IDs
        self.agents = list(observations.keys())
        self.num_agents = len(self.agents)
        
        # Get observation and action spaces
        self.observation_spaces = {}
        self.action_spaces = {}
        
        for agent_id in self.agents:
            self.observation_spaces[agent_id] = self.env.observation_space(agent_id)
            self.action_spaces[agent_id] = self.env.action_space(agent_id)
        
        print(f"Initialized {self.num_agents} agents: {self.agents}")
    
    def reset(self, seed: int = None) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Reset the environment.
        
        Args:
            seed: Random seed
            
        Returns:
            observations: Dictionary of observations for each agent
            infos: Dictionary of info for each agent
        """
        observations, infos = self.env.reset(seed=seed)
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
        
        # Calculate system-level metrics
        system_metrics = self._calculate_system_metrics(infos)
        
        # Add system metrics to infos
        for agent_id in self.agents:
            if agent_id in infos:
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
        # Extract metrics from infos
        waiting_times = []
        queues = []
        
        for agent_id, info in infos.items():
            # sumo-rl typically provides these metrics
            if 'system_total_waiting_time' in info:
                waiting_times.append(info['system_total_waiting_time'])
            if 'system_total_stopped' in info:
                queues.append(info['system_total_stopped'])
        
        return {
            'avg_waiting_time': np.mean(waiting_times) if waiting_times else 0.0,
            'total_waiting_time': np.sum(waiting_times) if waiting_times else 0.0,
            'avg_queue': np.mean(queues) if queues else 0.0,
            'total_queue': np.sum(queues) if queues else 0.0,
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
    Wrapper to manage multiple parallel SUMO environments for faster training.
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
        
        print(f"Initialized {num_envs} parallel environments")
    
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


def make_sumo_env(config: Dict[str, Any]) -> SumoRLWrapper:
    """
    Factory function to create a SUMO-RL environment.
    
    Args:
        config: Configuration dictionary with environment parameters
        
    Returns:
        Wrapped SUMO-RL environment
    """
    return SumoRLWrapper(
        net_file=config['net_file'],
        route_file=config['route_file'],
        use_gui=config.get('use_gui', False),
        num_seconds=config.get('num_seconds', 3600),
        delta_time=config.get('delta_time', 5),
        yellow_time=config.get('yellow_time', 2),
        min_green=config.get('min_green', 5),
        max_green=config.get('max_green', 50),
        sumo_seed=config.get('sumo_seed', 42),
        sumo_warnings=config.get('sumo_warnings', False),
        additional_sumo_cmd=config.get('additional_sumo_cmd', None)
    )

import sumo_rl
from modules.observation import CombinedObservation
from modules.reward import CombinedReward
from modules.logging_config import get_environment_logger

# Get module logger
logger = get_environment_logger()


class NeighborCombinedObservation(CombinedObservation):
    """
    Custom CombinedObservation that includes neighbor information and emergency vehicles.
    """
    def __init__(self, traffic_signal):
        super().__init__(
            traffic_signal,
            include_queue=True,
            include_waiting_time=True,
            include_wave=True,
            include_phase=True,
            include_emergency=True,  # Disable for now (model was trained without)
            include_neighbors=True,  # Enable neighbor observations
            neighbor_distance=1,
            include_neighbor_phase=True,
            include_neighbor_queue=True,
            include_neighbor_waiting_time=True,
            include_neighbor_actions=True,  # Enable neighbor actions
            normalize=True
        )



def combined_reward_wrapper(ts):
    """
    Wrapper to maintain stateful reward instance per traffic signal.
    Args:
        ts: TrafficSignal object
    Returns:
        float: Computed reward
    """
    if not hasattr(ts, 'reward_instance'):
        ts.reward_instance = CombinedReward(ts)
    return ts.reward_instance()


class Environment:
    def __init__(self, use_emergency_vehicles=True, use_gui=False):
        """
        Initialize traffic environment.
        
        Args:
            use_emergency_vehicles: If True, use route file with emergency vehicles (5%)
            use_gui: If True, show SUMO GUI (useful for visualizing emergency vehicles)
        """
        # Select route file based on emergency vehicles option
        route_file = ('configuration_files/grid4x4_realistic.rou.xml' 
                     if use_emergency_vehicles 
                     else 'configuration_files/grid4x4_no_emergency.rou.xml')
        
        logger.info(f"Initializing environment with route_file={route_file}, use_gui={use_gui}")
        
        self.env = sumo_rl.SumoEnvironment(net_file='configuration_files/grid4x4.net.xml',
                      route_file=route_file,
                      use_gui=use_gui,
                      observation_class=NeighborCombinedObservation,
                      reward_fn=combined_reward_wrapper,
                      delta_time=10,
                      yellow_time=5,
                      min_green=10,
                      max_green=50,
                      sumo_warnings=False,
                      num_seconds=1800)
        self.agents = self.env.ts_ids
        self.num_agents = len(self.agents)
        
        # IMPORTANT FIX: Each agent must have its own action space based on its number of phases
        self.action_spaces = {agent: self.env.action_spaces(agent) for agent in self.agents}
        self.observation_spaces = {agent: self.env.observation_spaces(agent) for agent in self.agents}
        self.rewards = {agent: 0 for agent in self.agents}
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}
        
        logger.info(f"Environment initialized with {self.num_agents} agents: {self.agents}")

    def reset(self):
        logger.debug("Resetting environment")
        observations = self.env.reset()
        return observations, {}

    def step(self, actions):
        """
        Step the environment with actions.
        
        Args:
            actions: Dictionary of agent_id -> action
            
        Returns:
            observations, rewards, terminations, truncations, infos
        """
        try:
            # Validate actions before stepping
            for agent_id, action in actions.items():
                action_space = self.action_spaces[agent_id]
                max_action = action_space.n if hasattr(action_space, 'n') else len(action_space)
                
                if action < 0 or action >= max_action:
                    logger.warning(f"Invalid action {action} for agent {agent_id} (max: {max_action-1}), clipping to valid range")
                    # Clip to valid range
                    actions[agent_id] = max(0, min(action, max_action - 1))
            
            observations, rewards, terminations, infos = self.env.step(actions)
            
        except KeyError as e:
            logger.error(f"Phase transition error: {e}")
            logger.error(f"Actions: {actions}")
            logger.error(f"Agent action spaces: {[(aid, self.action_spaces[aid].n) for aid in self.agents]}")
            raise
        
        # SumoEnvironment doesn't return truncations, so we'll create empty ones
        truncations = {agent: False for agent in self.agents}
        return observations, rewards, terminations, truncations, infos

    def close(self):
        if hasattr(self, 'env') and self.env is not None:
            logger.debug("Closing environment")
            self.env.close()

    def __del__(self):
        self.close()

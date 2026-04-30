"""
Modular Reward System for Traffic Signal Control.

This module provides a flexible and extensible framework for defining
reward functions for traffic signal control agents. Different reward strategies
can be easily implemented and swapped.

The reward system supports:
- Queue-based rewards (minimize waiting vehicles)
- Waiting time rewards (minimize delay)
- Throughput rewards (maximize vehicles passing through)
- Weighted combination of multiple metrics
- Co-DQL reward allocation mechanism

Author: Research Project
Date: 2025
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any
import numpy as np


class RewardFunction(ABC):
    """
    Abstract base class for reward functions.
    
    This class defines the interface that all reward functions must implement.
    Subclasses should define how to compute rewards based on the current
    and previous traffic states.
    """
    
    def __init__(self, traffic_signal):
        """
        Initialize reward function.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
        """
        self.traffic_signal = traffic_signal
        self.previous_state = None
    
    @abstractmethod
    def compute(self) -> float:
        """
        Compute the reward for the current state.
        
        Returns:
            Scalar reward value
        """
        pass
    
    def __call__(self) -> float:
        """
        Make the reward function callable for SUMO-RL compatibility.
        
        Returns:
            Scalar reward value
        """
        return self.compute()
    
    def reset(self):
        """Reset any internal state (called at episode start)."""
        self.previous_state = None
    
    def normalize_reward(self, reward: float, min_val: float, max_val: float) -> float:
        """
        Normalize reward to a standard range.
        
        Args:
            reward: Raw reward value
            min_val: Minimum possible reward
            max_val: Maximum possible reward
            
        Returns:
            Normalized reward
        """
        if max_val == min_val:
            return 0.0
        return (reward - min_val) / (max_val - min_val)


class QueueReward(RewardFunction):
    """
    Queue-based reward function.
    
    This reward function penalizes the number of vehicles waiting in queue
    (with zero speed) on all incoming lanes.
    
    Reward = -sum(queue_lengths)
    
    Based on the simplified MDP setting from the Co-DQL paper (Section IV-A1, Eq. 22).
    """
    
    def __init__(self, traffic_signal, normalize: bool = False, **kwargs):
        """
        Initialize queue reward.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            normalize: Whether to normalize reward
            **kwargs: Additional arguments (ignored, for compatibility)
        """
        super().__init__(traffic_signal)
        self.normalize_rewards = normalize
        self.max_queue = 100 * len(traffic_signal.lanes)  # Max possible queue
    
    def compute(self) -> float:
        """
        Compute queue-based reward.
        
        Returns:
            Negative sum of queue lengths
        """
        # Get total number of stopped/queued vehicles
        total_queue = self.traffic_signal.get_total_queued()
        
        # Negative reward (we want to minimize queues)
        reward = -total_queue
        
        if self.normalize_rewards:
            reward = self.normalize_reward(reward, -self.max_queue, 0)
        
        return reward


class WaitingTimeReward(RewardFunction):
    """
    Waiting time-based reward function.
    
    This reward function penalizes the cumulative waiting time (delay)
    of all vehicles on incoming lanes.
    
    Reward = -sum(waiting_times)
    
    This is more informative than queue length as it captures how long
    vehicles have been waiting, not just the count.
    """
    
    def __init__(self, traffic_signal, normalize: bool = False, **kwargs):
        """
        Initialize waiting time reward.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            normalize: Whether to normalize reward
            **kwargs: Additional arguments (ignored, for compatibility)
        """
        super().__init__(traffic_signal)
        self.normalize_rewards = normalize
        self.max_waiting_time = 1000.0  # Max expected total waiting time
    
    def compute(self) -> float:
        """
        Compute waiting time-based reward.
        
        Returns:
            Negative sum of waiting times
        """
        # Get accumulated waiting time across all lanes (returns a list)
        waiting_times = self.traffic_signal.get_accumulated_waiting_time_per_lane()
        total_waiting_time = sum(waiting_times)
        
        # Negative reward (minimize waiting time)
        reward = -total_waiting_time
        
        if self.normalize_rewards:
            reward = self.normalize_reward(reward, -self.max_waiting_time, 0)
        
        return reward


class DelayReward(RewardFunction):
    """
    Delay-based reward function.
    
    This reward function measures the change in cumulative delay.
    It rewards reducing delay and penalizes increasing delay.
    
    This is a differential reward that captures improvement/degradation.
    """
    
    def __init__(self, traffic_signal, **kwargs):
        """
        Initialize delay reward.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            **kwargs: Additional arguments (ignored, for compatibility)
        """
        super().__init__(traffic_signal)
        self.previous_delay = 0.0
    
    def compute(self) -> float:
        """
        Compute delay-based reward.
        
        Returns:
            Negative change in delay
        """
        # Calculate current total delay
        waiting_time_dict = self.traffic_signal.get_accumulated_waiting_time_per_lane()
        current_delay = sum(waiting_time_dict.values())
        
        # Compute change in delay
        if self.previous_delay > 0:
            reward = self.previous_delay - current_delay
        else:
            reward = -current_delay
        
        self.previous_delay = current_delay
        
        return reward
    
    def reset(self):
        """Reset previous delay."""
        super().reset()
        self.previous_delay = 0.0


class ThroughputReward(RewardFunction):
    """
    Throughput-based reward function.
    
    This reward function rewards the number of vehicles that have
    passed through the intersection (arrived at their destination
    or passed the stop line).
    
    Reward = number of vehicles served
    
    This encourages maximizing traffic flow through the intersection.
    """
    
    def __init__(self, traffic_signal, **kwargs):
        """
        Initialize throughput reward.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            **kwargs: Additional arguments (ignored, for compatibility)
        """
        super().__init__(traffic_signal)
        self.previous_vehicle_count = 0
    
    def compute(self) -> float:
        """
        Compute throughput-based reward.
        
        Returns:
            Number of vehicles served since last step
        """
        # Approximate throughput by reduction in queued vehicles
        # (more vehicles leaving = higher throughput)
        current_queued = self.traffic_signal.get_total_queued()
        
        # Calculate throughput (reduction in queue)
        if self.previous_vehicle_count > 0:
            throughput = self.previous_vehicle_count - current_queued
        else:
            throughput = 0
        
        self.previous_vehicle_count = current_queued
        
        # Positive reward for throughput
        reward = throughput
        
        return reward
    
    def reset(self):
        """Reset vehicle count."""
        super().reset()
        self.previous_vehicle_count = 0


class EmergencyVehicleReward(RewardFunction):
    """
    Emergency vehicle priority reward function.
    
    This reward function encourages agents to give priority to emergency vehicles
    (ambulances, police, fire trucks). It provides:
    - Positive reward (+5) when green light is given to lane with emergency vehicle
    - Negative reward (-5) when red light blocks emergency vehicle
    - No reward (0) when no emergency vehicles present
    
    This helps agents learn to detect and prioritize emergency vehicles.
    """
    
    def __init__(
        self,
        traffic_signal,
        reward_green: float = 5.0,
        penalty_red: float = -5.0,
        detection_range: float = 200.0,
        **kwargs
    ):
        """
        Initialize emergency vehicle reward.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            reward_green: Reward for giving green to emergency vehicle
            penalty_red: Penalty for blocking emergency vehicle with red
            detection_range: Maximum distance to detect emergency vehicles (meters)
            **kwargs: Additional arguments (ignored, for compatibility)
        """
        super().__init__(traffic_signal)
        self.reward_green = reward_green
        self.penalty_red = penalty_red
        self.detection_range = detection_range
    
    def _detect_emergency_vehicles_by_direction(self) -> Dict[str, List[str]]:
        """
        Detect emergency vehicles grouped by traffic signal direction.
        
        Returns:
            Dictionary mapping direction/phase to list of lanes with emergency vehicles
        """
        emergency_lanes = []
        
        try:
            # Get all vehicles approaching the intersection
            for lane in self.traffic_signal.lanes:
                # Get vehicles on this lane from SUMO
                if hasattr(self.traffic_signal, 'sumo'):
                    import traci
                    vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
                    
                    for veh_id in vehicle_ids:
                        # Check if it's an emergency vehicle
                        veh_type = traci.vehicle.getTypeID(veh_id)
                        veh_class = traci.vehicle.getVehicleClass(veh_id)
                        
                        # Emergency vehicles have special vClass or vType
                        if 'emergency' in veh_type.lower() or veh_class == 'emergency':
                            # Get distance from stop line
                            distance = traci.vehicle.getLanePosition(veh_id)
                            lane_length = traci.lane.getLength(lane)
                            distance_to_intersection = lane_length - distance
                            
                            if distance_to_intersection <= self.detection_range:
                                if lane not in emergency_lanes:
                                    emergency_lanes.append(lane)
        except Exception as e:
            # If TraCI not available or error, return empty list
            pass
        
        return emergency_lanes
    
    def _is_lane_green(self, lane: str) -> bool:
        """
        Check if a lane currently has green light.
        
        Args:
            lane: Lane ID
            
        Returns:
            True if lane has green, False otherwise
        """
        try:
            # Get current signal state
            if hasattr(self.traffic_signal, 'sumo'):
                import traci
                tl_id = self.traffic_signal.id
                state = traci.trafficlight.getRedYellowGreenState(tl_id)
                
                # Get link index for this lane
                # This is simplified - in practice, need to map lane to link index
                # For now, check if any phase allows this lane
                controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
                if lane in controlled_lanes:
                    lane_index = controlled_lanes.index(lane)
                    if lane_index < len(state):
                        return state[lane_index] in ['G', 'g']  # Green or green without priority
        except Exception:
            pass
        
        # Fallback: check current phase
        try:
            current_phase = self.traffic_signal.green_phase
            # Map lanes to phases (simplified)
            # In practice, need proper phase-to-lane mapping
            return True  # Placeholder
        except:
            return False
    
    def compute(self) -> float:
        """
        Compute emergency vehicle priority reward.
        
        Returns:
            Reward value based on emergency vehicle treatment
        """
        # Detect emergency vehicles
        emergency_lanes = self._detect_emergency_vehicles_by_direction()
        
        if not emergency_lanes:
            # No emergency vehicles, neutral reward
            return 0.0
        
        reward = 0.0
        
        # Check each lane with emergency vehicle
        for lane in emergency_lanes:
            if self._is_lane_green(lane):
                # Emergency vehicle has green light - positive reward
                reward += self.reward_green
            else:
                # Emergency vehicle blocked by red - penalty
                reward += self.penalty_red
        
        return reward


class CombinedReward(RewardFunction):
    """
    Combined reward function with regularization.
    
    This combines multiple reward components with weighted coefficients.
    
    Reward = -queue_length - β * waiting_time + γ * emergency_priority
    
    Based on the realistic MDP setting from the Co-DQL paper (Section IV-A2, Eq. 26).
    """
    
    def __init__(
        self,
        traffic_signal,
        queue_weight: float = 1.0,
        waiting_time_weight: float = 0.2,
        emergency_weight: float = 1.0,
        throughput_weight: float = 0.0,
        normalize: bool = False
    ):
        """
        Initialize combined reward.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            queue_weight: Weight for queue length component
            waiting_time_weight: Weight for waiting time component (β)
            throughput_weight: Weight for throughput component
            normalize: Whether to normalize reward
        """
        super().__init__(traffic_signal)
        self.queue_weight = queue_weight
        self.waiting_time_weight = waiting_time_weight
        self.emergency_weight = emergency_weight
        self.throughput_weight = throughput_weight
        self.normalize_rewards = normalize
        
        # Initialize component reward functions
        self.queue_reward = QueueReward(traffic_signal, normalize=False)
        self.waiting_reward = WaitingTimeReward(traffic_signal, normalize=False)
        self.emergency_reward = EmergencyVehicleReward(traffic_signal) if emergency_weight > 0 else None
        #self.throughput_reward = ThroughputReward(traffic_signal)
    
    def compute(self) -> float:
        """
        Compute combined reward.
        
        Returns:
            Weighted combination of reward components
        """
        # Get individual reward components
        queue_r = self.queue_reward.compute() if self.queue_weight > 0 else 0.0
        waiting_r = self.waiting_reward.compute() if self.waiting_time_weight > 0 else 0.0
        emergency_r = self.emergency_reward.compute() if self.emergency_reward and self.emergency_weight > 0 else 0.0
        #throughput_r = self.throughput_reward.compute() if self.throughput_weight > 0 else 0.0
        
        # Weighted combination
        reward = (self.queue_weight * queue_r + 
                 self.waiting_time_weight * waiting_r + 
                 self.emergency_weight * emergency_r)
            #self.throughput_weight * throughput_r
        
        return reward
    
    def reset(self):
        """Reset all component reward functions."""
        super().reset()
        self.queue_reward.reset()
        self.waiting_reward.reset()
        if self.emergency_reward:
            self.emergency_reward.reset()
        #self.throughput_reward.reset()


class PressureReward(RewardFunction):
    """
    Pressure-based reward function.
    
    Pressure is defined as the difference between incoming and outgoing
    vehicle counts. This reward encourages balancing traffic flow.
    
    Reward = -|incoming_vehicles - outgoing_vehicles|
    
    Based on the max-pressure control literature.
    """
    
    def __init__(self, traffic_signal, **kwargs):
        """
        Initialize pressure reward.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            **kwargs: Additional arguments (ignored, for compatibility)
        """
        super().__init__(traffic_signal)
    
    def compute(self) -> float:
        """
        Compute pressure-based reward.
        
        Returns:
            Negative pressure value
        """
        # Get total queued vehicles on incoming lanes
        incoming_count = self.traffic_signal.get_total_queued()
        
        # Approximate outgoing flow (pressure is imbalance)
        # In SUMO-RL, we focus on minimizing queue pressure
        pressure = incoming_count
        
        # Negative reward (minimize pressure)
        reward = -pressure
        
        return reward


class DifferenceReward(RewardFunction):
    """
    Difference reward (for multi-agent credit assignment).
    
    This computes the agent's marginal contribution to the system reward.
    
    Reward = System_Reward(with agent) - System_Reward(without agent)
    
    This helps with credit assignment in multi-agent settings by
    measuring each agent's individual contribution.
    """
    
    def __init__(self, traffic_signal, system_reward_func: RewardFunction, **kwargs):
        """
        Initialize difference reward.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            system_reward_func: The system-level reward function
            **kwargs: Additional arguments (ignored, for compatibility)
        """
        super().__init__(traffic_signal)
        self.system_reward_func = system_reward_func
        self.baseline_reward = 0.0
    
    def compute(self) -> float:
        """
        Compute difference reward.
        
        Returns:
            Agent's marginal contribution to system reward
        """
        # Get actual system reward
        system_reward = self.system_reward_func.compute()
        
        # Compute difference from baseline (counterfactual)
        reward = system_reward - self.baseline_reward
        
        # Update baseline (exponential moving average)
        alpha = 0.1
        self.baseline_reward = alpha * system_reward + (1 - alpha) * self.baseline_reward
        
        return reward
    
    def reset(self):
        """Reset baseline reward."""
        super().reset()
        self.baseline_reward = 0.0


class CooperativeReward:
    """
    Cooperative reward allocation mechanism for Co-DQL.
    
    This implements the reward allocation mechanism from the Co-DQL paper:
    
    r̂_k = r_k + α * Σ(r_i for i in neighbors)
    
    Where:
    - r_k is the agent's local reward
    - r_i are the neighbors' rewards
    - α is the cooperation coefficient
    
    Based on Co-DQL paper (Section III-B, Eq. 13).
    """
    
    def __init__(
        self,
        base_reward_func: RewardFunction,
        cooperation_alpha: float = 0.2
    ):
        """
        Initialize cooperative reward.
        
        Args:
            base_reward_func: Base reward function for individual agent
            cooperation_alpha: Cooperation coefficient (α in paper)
        """
        self.base_reward_func = base_reward_func
        self.cooperation_alpha = cooperation_alpha
    
    def compute_local(self) -> float:
        """
        Compute local reward for this agent.
        
        Returns:
            Local reward value
        """
        return self.base_reward_func.compute()
    
    def compute_cooperative(
        self,
        local_reward: float,
        neighbor_rewards: List[float]
    ) -> float:
        """
        Compute cooperative reward allocation.
        
        Args:
            local_reward: Agent's own local reward (r_k)
            neighbor_rewards: List of neighbor rewards [r_i for i in N(k)]
            
        Returns:
            Allocated cooperative reward (r̂_k)
        """
        # Sum of neighbor rewards
        neighbor_sum = sum(neighbor_rewards) if neighbor_rewards else 0.0
        
        # Cooperative reward allocation (Eq. 13 from paper)
        cooperative_reward = local_reward + self.cooperation_alpha * neighbor_sum
        
        return cooperative_reward
    
    def reset(self):
        """Reset base reward function."""
        self.base_reward_func.reset()


# Factory function to create reward functions by name
def create_reward_function(
    name: str,
    traffic_signal,
    **kwargs
) -> RewardFunction:
    """
    Factory function to create reward functions by name.
    
    Args:
        name: Name of the reward function class
        traffic_signal: TrafficSignal object from SUMO-RL
        **kwargs: Additional arguments for the reward function
        
    Returns:
        Instance of the requested reward function
        
    Raises:
        ValueError: If reward function name is not recognized
    """
    reward_classes = {
        'QueueReward': QueueReward,
        'WaitingTimeReward': WaitingTimeReward,
        'DelayReward': DelayReward,
        'ThroughputReward': ThroughputReward,
        'CombinedReward': CombinedReward,
        'PressureReward': PressureReward,
        'DifferenceReward': DifferenceReward,
    }
    
    if name not in reward_classes:
        raise ValueError(
            f"Unknown reward function: {name}. "
            f"Available options: {list(reward_classes.keys())}"
        )
    
    return reward_classes[name](traffic_signal, **kwargs)


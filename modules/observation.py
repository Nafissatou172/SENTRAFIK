"""
Modular Observation System for Traffic Signal Control.

This module provides a flexible and extensible framework for defining
observation spaces for traffic signal control agents. Different observation
strategies can be easily implemented and swapped.

The observation system is designed to work with SUMO-RL and supports:
- Queue-based observations
- Waiting time observations
- Wave (approaching vehicles) observations
- Combined observations

Author: Research Project
Date: 2025
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any
import numpy as np
import gymnasium as gym


class ObservationFunction(ABC):
    """
    Abstract base class for observation functions.
    
    This class defines the interface that all observation functions must implement.
    Subclasses should define how to extract state information from the traffic
    environment for each intersection/agent.
    """
    
    def __init__(self, traffic_signal):
        """
        Initialize observation function.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
        """
        self.traffic_signal = traffic_signal
    
    @abstractmethod
    def observation_space(self) -> gym.Space:
        """
        Define the observation space for this function.
        
        Returns:
            Gymnasium space object defining the observation space
        """
        pass
    
    @abstractmethod
    def compute(self) -> np.ndarray:
        """
        Compute the observation for the current state.
        
        Returns:
            Numpy array containing the observation
        """
        pass
    
    @abstractmethod
    def get_observation_size(self) -> int:
        """
        Get the size (dimension) of the observation vector.
        
        Returns:
            Integer size of observation
        """
        pass
    
    def __call__(self) -> np.ndarray:
        """
        Make the observation function callable for SUMO-RL compatibility.
        
        Returns:
            Observation array
        """
        return self.compute()
    
    def normalize(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normalize a value to [0, 1] range.
        
        Args:
            value: Value to normalize
            min_val: Minimum possible value
            max_val: Maximum possible value
            
        Returns:
            Normalized value in [0, 1]
        """
        if max_val == min_val:
            return 0.0
        return (value - min_val) / (max_val - min_val)


class QueueObservation(ObservationFunction):
    """
    Queue-based observation function.
    
    This observation function captures the number of vehicles with zero speed
    (waiting in queue) on each incoming lane of the intersection.
    
    Based on the simplified MDP setting from the Co-DQL paper (Section IV-A1).
    """
    
    def __init__(self, traffic_signal, normalize: bool = True):
        """
        Initialize queue observation.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            normalize: Whether to normalize observations to [0, 1]
        """
        super().__init__(traffic_signal)
        self.normalize_obs = normalize
        self.max_queue_length = 100  # Maximum expected queue length for normalization
    
    def observation_space(self) -> gym.Space:
        """
        Define observation space as Box with queue lengths for each lane.
        
        Returns:
            Box space with shape (num_lanes,)
        """
        num_lanes = len(self.traffic_signal.lanes)
        
        if self.normalize_obs:
            # Normalized to [0, 1]
            return gym.spaces.Box(
                low=0.0,
                high=1.0,
                shape=(num_lanes,),
                dtype=np.float32
            )
        else:
            # Raw queue counts
            return gym.spaces.Box(
                low=0,
                high=self.max_queue_length,
                shape=(num_lanes,),
                dtype=np.int32
            )
    

    def compute(self) -> np.ndarray:
        """
        Compute queue lengths for all incoming lanes.
        
        Returns:
            Array of queue lengths, one per incoming lane
        """
        # Get queue lengths for all lanes
        queue_lengths = self.traffic_signal.get_lanes_queue()
        
        if self.normalize_obs:
            # Normalize queue lengths
            normalized_queues = []
            for queue_length in queue_lengths:
                normalized_length = self.normalize(
                    queue_length, 
                    0, 
                    self.max_queue_length
                )
                normalized_queues.append(normalized_length)
            queue_lengths = normalized_queues
        
        return np.array(queue_lengths, dtype=np.float32)
    
    def get_observation_size(self) -> int:
        """Get observation dimension (number of lanes)."""
        return len(self.traffic_signal.lanes)


class WaitingTimeObservation(ObservationFunction):
    """
    Waiting time-based observation function.
    
    This observation captures the cumulative waiting time (delay) of vehicles
    on each incoming lane. This is more informative than just queue length
    as it captures how long vehicles have been waiting.
    
    Based on the realistic MDP setting from the Co-DQL paper (Section IV-A2).
    """
    
    def __init__(self, traffic_signal, normalize: bool = True):
        """
        Initialize waiting time observation.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            normalize: Whether to normalize observations to [0, 1]
        """
        super().__init__(traffic_signal)
        self.normalize_obs = normalize
        self.max_waiting_time = 300.0  # Maximum expected waiting time (seconds)
    
    def observation_space(self) -> gym.Space:
        """
        Define observation space for waiting times.
        
        Returns:
            Box space with shape (num_lanes,)
        """
        num_lanes = len(self.traffic_signal.lanes)
        
        return gym.spaces.Box(
            low=0.0,
            high=1.0 if self.normalize_obs else self.max_waiting_time,
            shape=(num_lanes,),
            dtype=np.float32
        )
    
    def compute(self) -> np.ndarray:
        """
        Compute cumulative waiting time for all incoming lanes.
        
        Returns:
            Array of waiting times, one per incoming lane
        """
        # Get accumulated waiting time per lane (returns a list)
        waiting_times = self.traffic_signal.get_accumulated_waiting_time_per_lane()
        
        if self.normalize_obs:
            # Normalize waiting times
            normalized_times = []
            for waiting_time in waiting_times:
                normalized_time = self.normalize(
                    waiting_time,
                    0,
                    self.max_waiting_time
                )
                normalized_times.append(normalized_time)
            waiting_times = normalized_times
        
        return np.array(waiting_times, dtype=np.float32)
    
    def get_observation_size(self) -> int:
        """Get observation dimension (number of lanes)."""
        return len(self.traffic_signal.lanes)


class WaveObservation(ObservationFunction):
    """
    Wave (approaching vehicles) observation function.
    
    This observation captures the total number of approaching vehicles
    on each incoming lane, providing information about incoming traffic flow.
    
    Based on the realistic MDP setting from the Co-DQL paper (Section IV-A2).
    """
    
    def __init__(self, traffic_signal, detection_distance: float = 100.0, normalize: bool = True):
        """
        Initialize wave observation.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            detection_distance: Distance (meters) to detect approaching vehicles
            normalize: Whether to normalize observations to [0, 1]
        """
        super().__init__(traffic_signal)
        self.detection_distance = detection_distance
        self.normalize_obs = normalize
        self.max_vehicles = 50  # Maximum expected vehicles in detection range
    
    def observation_space(self) -> gym.Space:
        """
        Define observation space for approaching vehicles.
        
        Returns:
            Box space with shape (num_lanes,)
        """
        num_lanes = len(self.traffic_signal.lanes)
        
        return gym.spaces.Box(
            low=0.0,
            high=1.0 if self.normalize_obs else self.max_vehicles,
            shape=(num_lanes,),
            dtype=np.float32
        )
    
    def compute(self) -> np.ndarray:
        """
        Compute number of approaching vehicles for all incoming lanes.
        
        Returns:
            Array of vehicle counts, one per incoming lane
        """
        # Get density of vehicles per lane
        lane_densities = self.traffic_signal.get_lanes_density()
        
        if self.normalize_obs:
            # Normalize densities
            normalized_densities = []
            for density in lane_densities:
                normalized_density = self.normalize(
                    density,
                    0,
                    self.max_vehicles
                )
                normalized_densities.append(normalized_density)
            lane_densities = normalized_densities
        
        return np.array(lane_densities, dtype=np.float32)
    
    def get_observation_size(self) -> int:
        """Get observation dimension (number of lanes)."""
        return len(self.traffic_signal.lanes)


class NeighborObservation(ObservationFunction):
    """
    Neighbor observation function that captures observations from neighboring traffic signals.
    
    This observation function aggregates information from neighboring traffic signals
    to provide context about the surrounding traffic situation. It can be used to
    implement cooperative multi-agent traffic control.
    """
    
    def __init__(
        self, 
        traffic_signal, 
        neighbor_distance: int = 1,
        include_neighbor_phase: bool = True,
        include_neighbor_queue: bool = True,
        include_neighbor_waiting_time: bool = True,
        include_neighbor_actions: bool = True,
        normalize: bool = True
    ):
        """
        Initialize neighbor observation.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            neighbor_distance: Maximum distance (hops) to consider as neighbors
            include_neighbor_phase: Include neighboring traffic signal phases
            include_neighbor_queue: Include neighboring traffic signal queue lengths
            include_neighbor_waiting_time: Include neighboring traffic signal waiting times
            include_neighbor_actions: Include neighboring traffic signal actions (last taken actions)
            normalize: Whether to normalize observations
        """
        super().__init__(traffic_signal)
        self.neighbor_distance = neighbor_distance
        self.include_neighbor_phase = include_neighbor_phase
        self.include_neighbor_queue = include_neighbor_queue
        self.include_neighbor_waiting_time = include_neighbor_waiting_time
        self.include_neighbor_actions = include_neighbor_actions
        self.normalize_obs = normalize
        
        # Neighbors will be determined when first needed
        self.neighbors = None
        
        # Initialize observation functions for neighbors
        if include_neighbor_queue:
            self.queue_obs = QueueObservation(traffic_signal, normalize=normalize)
        if include_neighbor_waiting_time:
            self.waiting_obs = WaitingTimeObservation(traffic_signal, normalize=normalize)
    
    def _get_neighbors(self) -> List[str]:
        """
        Get list of neighboring traffic signal IDs.
        
        For simplicity, we consider all other traffic signals as neighbors.
        In a real implementation, you would use network topology to find
        actual neighboring intersections.
        
        Returns:
            List of neighbor traffic signal IDs
        """
        try:
            all_ts_ids = list(self.traffic_signal.env.traffic_signals.keys())
            return [ts_id for ts_id in all_ts_ids if ts_id != self.traffic_signal.id]
        except AttributeError:
            # Traffic signals not yet initialized, return empty list
            # This will be updated when compute() is first called
            return []
    
    def observation_space(self) -> gym.Space:
        """Define observation space for neighbor observations."""
        total_size = self.get_observation_size()
        
        return gym.spaces.Box(
            low=0.0,
            high=1.0 if self.normalize_obs else np.inf,
            shape=(total_size,),
            dtype=np.float32
        )
    
    def compute(self) -> np.ndarray:
        """
        Compute neighbor observations.
        
        Returns:
            Concatenated observation array from all neighbors
        """
        # Get neighbors if not already determined
        if self.neighbors is None:
            self.neighbors = self._get_neighbors()
        
        neighbor_observations = []
        
        for neighbor_id in self.neighbors:
            neighbor_ts = self.traffic_signal.env.traffic_signals[neighbor_id]
            neighbor_obs = []
            
            # Get neighbor's current phase
            if self.include_neighbor_phase:
                num_phases = neighbor_ts.num_green_phases
                current_phase = neighbor_ts.green_phase
                phase_one_hot = np.zeros(num_phases, dtype=np.float32)
                if current_phase < num_phases:
                    phase_one_hot[current_phase] = 1.0
                neighbor_obs.append(phase_one_hot)
            
            # Get neighbor's queue length (simplified - total queue across all lanes)
            if self.include_neighbor_queue:
                try:
                    queue_lengths = neighbor_ts.get_lanes_queue()
                    total_queue = sum(queue_lengths) if queue_lengths else 0.0
                    if self.normalize_obs:
                        # Normalize by maximum expected queue length
                        max_queue = len(neighbor_ts.lanes) * 10  # Assume max 10 vehicles per lane
                        total_queue = self.normalize(total_queue, 0, max_queue)
                    neighbor_obs.append(np.array([total_queue], dtype=np.float32))
                except:
                    # Fallback if queue method is not available
                    neighbor_obs.append(np.array([0.0], dtype=np.float32))
            
            # Get neighbor's waiting time (simplified - total waiting time across all lanes)
            if self.include_neighbor_waiting_time:
                try:
                    waiting_times = neighbor_ts.get_accumulated_waiting_time_per_lane()
                    total_waiting = sum(waiting_times) if waiting_times else 0.0
                    if self.normalize_obs:
                        # Normalize by maximum expected waiting time
                        max_waiting = len(neighbor_ts.lanes) * 100  # Assume max 100 seconds per lane
                        total_waiting = self.normalize(total_waiting, 0, max_waiting)
                    neighbor_obs.append(np.array([total_waiting], dtype=np.float32))
                except:
                    # Fallback if waiting time method is not available
                    neighbor_obs.append(np.array([0.0], dtype=np.float32))
            
            # Get neighbor's last action (current phase as proxy for last taken action)
            if self.include_neighbor_actions:
                try:
                    # Use current phase as the last action taken
                    last_action = neighbor_ts.green_phase
                    # One-hot encode the action
                    action_one_hot = np.zeros(neighbor_ts.num_green_phases, dtype=np.float32)
                    if last_action < neighbor_ts.num_green_phases:
                        action_one_hot[last_action] = 1.0
                    neighbor_obs.append(action_one_hot)
                except:
                    # Fallback if action is not available
                    num_phases = 4  # Default assumption
                    neighbor_obs.append(np.zeros(num_phases, dtype=np.float32))
            
            # Concatenate this neighbor's observations
            if neighbor_obs:
                neighbor_observations.extend(neighbor_obs)
        
        if neighbor_observations:
            return np.concatenate(neighbor_observations)
        else:
            # Return empty array if no neighbors or no observations
            return np.array([], dtype=np.float32)
    
    def __call__(self) -> np.ndarray:
        """
        Make the observation function callable for SUMO-RL compatibility.
        
        Returns:
            Observation array
        """
        return self.compute()
    
    def get_observation_size(self) -> int:
        """Get total observation dimension."""
        # Get neighbors if not already determined
        if self.neighbors is None:
            self.neighbors = self._get_neighbors()
        
        size = 0
        
        # If neighbors list is empty (during initialization), estimate size
        if not self.neighbors:
            # Estimate based on typical grid4x4 setup: 15 neighbors, 4 phases each
            estimated_neighbors = 15  # 16 total signals - 1 (self) = 15 neighbors
            if self.include_neighbor_phase:
                size += estimated_neighbors * 4  # Assume 4 phases per signal
            if self.include_neighbor_queue:
                size += estimated_neighbors
            if self.include_neighbor_waiting_time:
                size += estimated_neighbors
            if self.include_neighbor_actions:
                size += estimated_neighbors * 4  # Assume 4 actions per signal
        else:
            for neighbor_id in self.neighbors:
                try:
                    neighbor_ts = self.traffic_signal.env.traffic_signals[neighbor_id]
                    
                    if self.include_neighbor_phase:
                        size += neighbor_ts.num_green_phases
                    
                    if self.include_neighbor_queue:
                        size += 1  # Total queue length
                    
                    if self.include_neighbor_waiting_time:
                        size += 1  # Total waiting time
                    
                    if self.include_neighbor_actions:
                        size += neighbor_ts.num_green_phases  # One-hot encoded action
                except (KeyError, AttributeError):
                    # Neighbor not available yet, skip
                    continue
        
        return size


class EmergencyVehicleObservation(ObservationFunction):
    """
    Emergency vehicle detection observation function.
    
    This observation detects emergency vehicles (ambulance, police, fire trucks)
    approaching or waiting at the intersection. It provides:
    - Binary indicator per lane (1 if emergency vehicle present, 0 otherwise)
    - Distance to closest emergency vehicle per lane (normalized)
    - Type of emergency vehicle (encoded)
    
    This allows agents to learn to prioritize emergency vehicles.
    """
    
    def __init__(self, traffic_signal, normalize: bool = True, detection_range: float = 200.0):
        """
        Initialize emergency vehicle observation.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            normalize: Whether to normalize observations
            detection_range: Maximum distance to detect emergency vehicles (meters)
        """
        super().__init__(traffic_signal)
        self.normalize_obs = normalize
        self.detection_range = detection_range
        
        # Emergency vehicle types in SUMO
        self.emergency_types = ['emergency', 'authority']  # SUMO vTypes
    
    def observation_space(self) -> gym.Space:
        """
        Define observation space for emergency vehicles.
        
        Returns:
            Box space with emergency vehicle indicators
        """
        num_lanes = len(self.traffic_signal.lanes)
        
        # For each lane: [has_emergency (0/1), distance_normalized, type_encoded]
        # Total: num_lanes * 3
        return gym.spaces.Box(
            low=0.0,
            high=1.0,
            shape=(num_lanes * 3,),
            dtype=np.float32
        )
    
    def _detect_emergency_vehicles(self) -> List[Tuple[str, float, str]]:
        """
        Detect emergency vehicles on incoming lanes.
        
        Returns:
            List of (lane_id, distance, vehicle_type) for each emergency vehicle
        """
        emergency_vehicles = []
        
        try:
            # Get all vehicles approaching the intersection
            for lane in self.traffic_signal.lanes:
                # Get vehicles on this lane from SUMO
                # Note: This requires TraCI access
                if hasattr(self.traffic_signal, 'sumo'):
                    import traci
                    vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
                    
                    for veh_id in vehicle_ids:
                        # Check if it's an emergency vehicle
                        veh_type = traci.vehicle.getTypeID(veh_id)
                        veh_class = traci.vehicle.getVehicleClass(veh_id)
                        
                        # Emergency vehicles have special vClass or vType
                        if 'emergency' in veh_type.lower() or veh_class == 'emergency':
                            #print(f"Emergency vehicle detected: {veh_id} on lane {lane}")
                            # Get distance from stop line
                            distance = traci.vehicle.getLanePosition(veh_id)
                            lane_length = traci.lane.getLength(lane)
                            distance_to_intersection = lane_length - distance
                            
                            if distance_to_intersection <= self.detection_range:
                                emergency_vehicles.append((lane, distance_to_intersection, veh_type))
        except Exception as e:
            # If TraCI not available or error, return empty list
            pass
        
        return emergency_vehicles
    
    def compute(self) -> np.ndarray:
        """
        Compute emergency vehicle observation.
        
        Returns:
            Array with emergency vehicle information per lane
        """
        num_lanes = len(self.traffic_signal.lanes)
        observation = np.zeros(num_lanes * 3, dtype=np.float32)
        
        # Detect emergency vehicles
        emergency_vehicles = self._detect_emergency_vehicles()
        
        # Build observation vector
        for i, lane in enumerate(self.traffic_signal.lanes):
            # Find emergency vehicles on this lane
            lane_emergencies = [ev for ev in emergency_vehicles if ev[0] == lane]
            
            if lane_emergencies:
                # Has emergency vehicle
                observation[i * 3] = 1.0
                
                # Distance to closest emergency vehicle (normalized)
                min_distance = min([ev[1] for ev in lane_emergencies])
                if self.normalize_obs:
                    observation[i * 3 + 1] = 1.0 - self.normalize(min_distance, 0, self.detection_range)
                else:
                    observation[i * 3 + 1] = min_distance
                
                # Type encoding (simplified: 1.0 for emergency, 0.5 for authority)
                veh_type = lane_emergencies[0][2]
                if 'emergency' in veh_type.lower():
                    observation[i * 3 + 2] = 1.0
                elif 'authority' in veh_type.lower():
                    observation[i * 3 + 2] = 0.5
            else:
                # No emergency vehicle
                observation[i * 3] = 0.0
                observation[i * 3 + 1] = 0.0
                observation[i * 3 + 2] = 0.0
        
        return observation
    
    def get_observation_size(self) -> int:
        """Get observation dimension (3 per lane)."""
        return len(self.traffic_signal.lanes) * 3


class CombinedObservation(ObservationFunction):
    """
    Combined observation function that concatenates multiple observation types.
    
    This allows creating rich observation spaces by combining different
    observation functions (e.g., queue + waiting time + wave + emergency vehicles).
    
    Based on the realistic MDP setting from the Co-DQL paper which uses
    both waiting time and wave observations (Equation 25).
    """
    
    def __init__(
        self, 
        traffic_signal,
        include_queue: bool = True,
        include_waiting_time: bool = True,
        include_wave: bool = True,
        include_phase: bool = True,
        include_emergency: bool = False,
        include_neighbors: bool = False,
        neighbor_distance: int = 1,
        include_neighbor_phase: bool = True,
        include_neighbor_queue: bool = True,
        include_neighbor_waiting_time: bool = True,
        include_neighbor_actions: bool = True,
        normalize: bool = True
    ):
        """
        Initialize combined observation.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            include_queue: Include queue length observations
            include_waiting_time: Include waiting time observations
            include_wave: Include wave (approaching vehicles) observations
            include_phase: Include current phase as one-hot encoding
            include_neighbors: Include neighbor traffic signal observations
            neighbor_distance: Maximum distance to consider as neighbors
            include_neighbor_phase: Include neighboring traffic signal phases
            include_neighbor_queue: Include neighboring traffic signal queue lengths
            include_neighbor_waiting_time: Include neighboring traffic signal waiting times
            include_neighbor_actions: Include neighboring traffic signal actions
            normalize: Whether to normalize observations
        """
        super().__init__(traffic_signal)
        self.include_queue = include_queue
        self.include_waiting_time = include_waiting_time
        self.include_wave = include_wave
        self.include_phase = include_phase
        self.include_emergency = include_emergency
        self.include_neighbors = include_neighbors
        self.normalize_obs = normalize
        
        # Initialize sub-observation functions
        self.obs_functions = []
        
        if include_queue:
            self.obs_functions.append(
                QueueObservation(traffic_signal, normalize=normalize)
            )
        
        if include_waiting_time:
            self.obs_functions.append(
                WaitingTimeObservation(traffic_signal, normalize=normalize)
            )
        
        if include_wave:
            self.obs_functions.append(
                WaveObservation(traffic_signal, normalize=normalize)
            )
        
        if include_emergency:
            self.obs_functions.append(
                EmergencyVehicleObservation(traffic_signal, normalize=normalize)
            )
        
        if include_neighbors:
            self.obs_functions.append(
                NeighborObservation(
                    traffic_signal, 
                    neighbor_distance=neighbor_distance,
                    include_neighbor_phase=include_neighbor_phase,
                    include_neighbor_queue=include_neighbor_queue,
                    include_neighbor_waiting_time=include_neighbor_waiting_time,
                    include_neighbor_actions=include_neighbor_actions,
                    normalize=normalize
                )
            )
    
    def observation_space(self) -> gym.Space:
        """
        Define combined observation space.
        
        Returns:
            Box space with concatenated observations
        """
        total_size = self.get_observation_size()
        
        return gym.spaces.Box(
            low=0.0,
            high=1.0 if self.normalize_obs else np.inf,
            shape=(total_size,),
            dtype=np.float32
        )
    
    def compute(self) -> np.ndarray:
        """
        Compute combined observation by concatenating all sub-observations.
        
        Returns:
            Concatenated observation array
        """
        observations = []
        
        # Get observations from all sub-functions
        for obs_func in self.obs_functions:
            observations.append(obs_func.compute())
        
        # Add current phase as one-hot encoding if requested
        if self.include_phase:
            num_phases = self.traffic_signal.num_green_phases
            current_phase = self.traffic_signal.green_phase
            phase_one_hot = np.zeros(num_phases, dtype=np.float32)
            if current_phase < num_phases:
                phase_one_hot[current_phase] = 1.0
            observations.append(phase_one_hot)
        
        # Concatenate all observations
        return np.concatenate(observations)
    
    def __call__(self) -> np.ndarray:
        """
        Make the observation function callable for SUMO-RL compatibility.
        
        Returns:
            Observation array
        """
        return self.compute()
    
    def get_observation_size(self) -> int:
        """Get total observation dimension."""
        size = sum(obs_func.get_observation_size() for obs_func in self.obs_functions)
        
        if self.include_phase:
            size += self.traffic_signal.num_green_phases
        
        return size


class DensityObservation(ObservationFunction):
    """
    Density-based observation function.
    
    This observation captures the density (vehicles per meter) on each
    incoming lane, which is useful for understanding congestion levels.
    """
    
    def __init__(self, traffic_signal, normalize: bool = True):
        """
        Initialize density observation.
        
        Args:
            traffic_signal: TrafficSignal object from SUMO-RL
            normalize: Whether to normalize observations to [0, 1]
        """
        super().__init__(traffic_signal)
        self.normalize_obs = normalize
        self.max_density = 0.2  # Maximum expected density (vehicles/meter)
    
    def observation_space(self) -> gym.Space:
        """Define observation space for lane densities."""
        num_lanes = len(self.traffic_signal.lanes)
        
        return gym.spaces.Box(
            low=0.0,
            high=1.0 if self.normalize_obs else self.max_density,
            shape=(num_lanes,),
            dtype=np.float32
        )
    
    def compute(self) -> np.ndarray:
        """
        Compute density for all incoming lanes.
        
        Returns:
            Array of densities, one per incoming lane
        """
        densities = []
        # Approximate density from queued vehicles
        total_queued = self.traffic_signal.get_total_queued()
        num_lanes = len(self.traffic_signal.lanes)
        
        for lane in self.traffic_signal.lanes:
            # Approximate density per lane (vehicles per lane)
            density = total_queued / num_lanes if num_lanes > 0 else 0
            
            if self.normalize_obs:
                density = self.normalize(density, 0, self.max_density)
            
            densities.append(density)
        
        return np.array(densities, dtype=np.float32)
    
    def get_observation_size(self) -> int:
        """Get observation dimension (number of lanes)."""
        return len(self.traffic_signal.lanes)


# Factory function to create observation functions by name
def create_observation_function(
    name: str,
    traffic_signal,
    **kwargs
) -> ObservationFunction:
    """
    Factory function to create observation functions by name.
    
    Args:
        name: Name of the observation function class
        traffic_signal: TrafficSignal object from SUMO-RL
        **kwargs: Additional arguments for the observation function
        
    Returns:
        Instance of the requested observation function
        
    Raises:
        ValueError: If observation function name is not recognized
    """
    observation_classes = {
        'QueueObservation': QueueObservation,
        'WaitingTimeObservation': WaitingTimeObservation,
        'WaveObservation': WaveObservation,
        'CombinedObservation': CombinedObservation,
        'DensityObservation': DensityObservation,
    }
    
    if name not in observation_classes:
        raise ValueError(
            f"Unknown observation function: {name}. "
            f"Available options: {list(observation_classes.keys())}"
        )
    
    return observation_classes[name](traffic_signal, **kwargs)


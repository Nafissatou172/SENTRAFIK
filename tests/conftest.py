"""
Pytest configuration and fixtures for Oraban tests.

Provides mock objects and fixtures for testing observation/reward functions
without requiring SUMO to be running.
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from typing import Dict, List
from typing import Dict, List


class MockTrafficSignal:
    """Mock TrafficSignal for testing observation and reward functions."""
    
    def __init__(
        self,
        ts_id: str = "t1",
        num_lanes: int = 4,
        num_phases: int = 4,
        current_phase: int = 0,
        queue_lengths: List[int] = None,
        waiting_times: List[float] = None,
        approaching_vehicles: List[int] = None,
        neighbors: List[str] = None,
    ):
        self.id = ts_id
        self.lanes = [f"{ts_id}_lane_{i}" for i in range(num_lanes)]
        self.num_phases = num_phases
        self.current_phase = current_phase
        
        # Default values if not provided
        self.queue_lengths = queue_lengths or [0] * num_lanes
        self.waiting_times = waiting_times or [0.0] * num_lanes
        self.approaching_vehicles = approaching_vehicles or [0] * num_lanes
        self.neighbors = neighbors or []
        
        # Mock the sumo attribute
        self.sumo = MagicMock()
        
    def get_lanes_queue(self) -> List[int]:
        """Get queue length for each lane."""
        return self.queue_lengths
    
    def get_accumulated_waiting_time_per_lane(self) -> List[float]:
        """Get waiting time for each lane."""
        return self.waiting_times
    
    def get_lanes_density(self) -> List[float]:
        """Get density (vehicles/length) for each lane."""
        return [q / 100.0 for q in self.queue_lengths]  # Normalized
    
    def get_lanes_count(self) -> List[int]:
        """Get count of approaching vehicles per lane."""
        return self.approaching_vehicles
    
    def get_total_queued(self) -> int:
        """Get total queued vehicles across all lanes."""
        return sum(self.queue_lengths)
    
    def get_pressure(self) -> float:
        """Get pressure metric."""
        return float(sum(self.queue_lengths))
    
    def get_average_speed(self) -> float:
        """Get average speed of vehicles."""
        return 10.0  # Default speed
    
    def get_out_lanes_density(self) -> List[float]:
        """Get outgoing lane densities."""
        return [0.1] * len(self.lanes)
    
    def get_neighbor_ids(self) -> List[str]:
        """Get neighbor traffic signal IDs."""
        return self.neighbors


class MockEnvironment:
    """Mock SUMO environment for testing."""
    
    def __init__(
        self,
        num_agents: int = 4,
        num_lanes: int = 4,
        num_phases: int = 4,
    ):
        self.ts_ids = [f"t{i+1}" for i in range(num_agents)]
        self.traffic_signals = {
            ts_id: MockTrafficSignal(
                ts_id=ts_id,
                num_lanes=num_lanes,
                num_phases=num_phases,
            )
            for ts_id in self.ts_ids
        }
        self.num_agents = num_agents
        
    def reset(self):
        """Reset environment."""
        return {ts_id: np.zeros(10) for ts_id in self.ts_ids}
    
    def step(self, actions: Dict[str, int]):
        """Execute step with actions."""
        observations = {ts_id: np.zeros(10) for ts_id in self.ts_ids}
        rewards = {ts_id: 0.0 for ts_id in self.ts_ids}
        terminations = {ts_id: False for ts_id in self.ts_ids}
        infos = {ts_id: {} for ts_id in self.ts_ids}
        return observations, rewards, terminations, infos


@pytest.fixture
def mock_traffic_signal():
    """Create a mock traffic signal with default settings."""
    return MockTrafficSignal()


@pytest.fixture
def mock_traffic_signal_with_data():
    """Create a mock traffic signal with sample data."""
    return MockTrafficSignal(
        ts_id="t1",
        num_lanes=4,
        num_phases=4,
        current_phase=0,
        queue_lengths=[5, 3, 8, 2],
        waiting_times=[10.5, 5.2, 20.1, 3.0],
        approaching_vehicles=[10, 8, 15, 5],
        neighbors=["t2", "t3"],
    )


@pytest.fixture
def mock_environment():
    """Create a mock environment."""
    return MockEnvironment()


@pytest.fixture
def sample_config():
    """Return sample configuration dictionary."""
    return {
        'environment': {
            'net_file': 'test_network.net.xml',
            'delta_time': 10,
            'use_gui': False,
        },
        'training': {
            'learning_rate': 0.0003,
            'batch_size': 256,
        },
        'logging': {
            'level': 'DEBUG',
        },
    }

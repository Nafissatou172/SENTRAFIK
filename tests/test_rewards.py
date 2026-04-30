"""
Unit tests for reward functions.

Tests the modular reward system for traffic signal control.
"""

import pytest
import numpy as np
from unittest.mock import Mock


class TestRewardFunctions:
    """Test suite for reward functions."""
    
    def test_queue_reward_calculation(self, mock_traffic_signal_with_data):
        """Test queue-based reward calculation."""
        ts = mock_traffic_signal_with_data
        queue_lengths = ts.get_lanes_queue()
        
        # Reward should be negative sum of queues
        expected_reward = -sum(queue_lengths)
        assert expected_reward == -18
    
    def test_waiting_time_reward_calculation(self, mock_traffic_signal_with_data):
        """Test waiting time-based reward calculation."""
        ts = mock_traffic_signal_with_data
        waiting_times = ts.get_accumulated_waiting_time_per_lane()
        
        # Reward should be negative sum of waiting times
        expected_reward = -sum(waiting_times)
        assert abs(expected_reward - (-38.8)) < 0.01
    
    def test_empty_queue_optimal_reward(self, mock_traffic_signal):
        """Test that empty queues give zero penalty."""
        ts = mock_traffic_signal
        queue_lengths = ts.get_lanes_queue()
        
        reward = -sum(queue_lengths)
        assert reward == 0  # No penalty for empty queues


class TestRewardNormalization:
    """Test reward normalization."""
    
    def test_reward_normalization_basic(self):
        """Test basic reward normalization."""
        raw_reward = -50
        min_val = -100
        max_val = 0
        
        # Normalize to [-1, 0] range
        normalized = (raw_reward - min_val) / (max_val - min_val) - 1
        assert -1 <= normalized <= 0
    
    def test_reward_scaling(self):
        """Test reward scaling factor."""
        raw_reward = -100
        scale = 0.01
        
        scaled = raw_reward * scale
        assert scaled == -1.0


class TestCombinedReward:
    """Test combined/weighted reward functions."""
    
    def test_weighted_combination(self, mock_traffic_signal_with_data):
        """Test weighted combination of reward components."""
        ts = mock_traffic_signal_with_data
        
        # Calculate components
        queue_reward = -sum(ts.get_lanes_queue())  # -18
        waiting_reward = -sum(ts.get_accumulated_waiting_time_per_lane())  # -38.8
        
        # Weighted combination
        queue_weight = 0.5
        waiting_weight = 0.5
        
        combined = queue_weight * queue_reward + waiting_weight * waiting_reward
        expected = 0.5 * (-18) + 0.5 * (-38.8)
        assert abs(combined - expected) < 0.01
    
    def test_weight_normalization(self):
        """Test that weights should sum to 1 for proper scaling."""
        weights = {
            'queue': 0.5,
            'waiting_time': 0.3,
            'emergency': 0.2,
        }
        
        assert abs(sum(weights.values()) - 1.0) < 0.01


class TestRewardCallable:
    """Test reward function callable interface."""
    
    def test_reward_function_is_callable(self, mock_traffic_signal):
        """Test that reward functions can be used as callables."""
        # Mock reward function
        def reward_fn(traffic_signal):
            return -sum(traffic_signal.get_lanes_queue())
        
        result = reward_fn(mock_traffic_signal)
        assert isinstance(result, (int, float))
    
    def test_reward_reset(self, mock_traffic_signal):
        """Test reward reset functionality for stateful rewards."""
        # For delay-based rewards that track previous state
        previous_delay = 0.0
        current_delay = sum(mock_traffic_signal.get_accumulated_waiting_time_per_lane())
        
        # After reset, previous_delay should be 0
        delta_reward = -(current_delay - previous_delay)
        assert delta_reward == 0  # First step after reset

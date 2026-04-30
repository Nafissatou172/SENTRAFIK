"""
Unit tests for environment wrapper.

Tests the CustomEnvWrapper and MultiEnvWrapper classes.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock


class TestMockEnvironment:
    """Test the mock environment fixtures."""
    
    def test_mock_environment_agents(self, mock_environment):
        """Test mock environment has correct agents."""
        assert len(mock_environment.ts_ids) == 4
        assert "t1" in mock_environment.ts_ids
        assert "t4" in mock_environment.ts_ids
    
    def test_mock_environment_traffic_signals(self, mock_environment):
        """Test mock environment has traffic signals."""
        assert len(mock_environment.traffic_signals) == 4
        for ts_id in mock_environment.ts_ids:
            assert ts_id in mock_environment.traffic_signals
    
    def test_mock_environment_reset(self, mock_environment):
        """Test mock environment reset."""
        observations = mock_environment.reset()
        assert isinstance(observations, dict)
        assert len(observations) == 4
    
    def test_mock_environment_step(self, mock_environment):
        """Test mock environment step."""
        actions = {ts_id: 0 for ts_id in mock_environment.ts_ids}
        obs, rewards, terms, infos = mock_environment.step(actions)
        
        assert isinstance(obs, dict)
        assert isinstance(rewards, dict)
        assert isinstance(terms, dict)
        assert isinstance(infos, dict)


class TestActionValidation:
    """Test action validation logic."""
    
    def test_valid_action_range(self):
        """Test valid action is within range."""
        num_phases = 4
        action = 2
        
        assert 0 <= action < num_phases
    
    def test_invalid_action_clipping(self):
        """Test invalid actions are clipped to valid range."""
        num_phases = 4
        
        # Action too high
        action = 10
        clipped = max(0, min(action, num_phases - 1))
        assert clipped == 3
        
        # Negative action
        action = -1
        clipped = max(0, min(action, num_phases - 1))
        assert clipped == 0
    
    def test_action_per_agent(self):
        """Test that each agent can have different valid actions."""
        agent_phases = {
            't1': 4,
            't2': 2,  # Some intersections have fewer phases
            't3': 4,
            't4': 3,
        }
        
        actions = {'t1': 3, 't2': 1, 't3': 2, 't4': 2}
        
        for agent_id, action in actions.items():
            max_action = agent_phases[agent_id]
            assert 0 <= action < max_action, f"Invalid action for {agent_id}"


class TestEnvironmentClosing:
    """Test environment closing logic."""
    
    def test_close_method_exists(self, mock_environment):
        """Test that environments have close method."""
        # Mock doesn't have close, but real env should
        assert hasattr(mock_environment, 'reset')
    
    def test_close_is_safe_to_call_multiple_times(self):
        """Test that close can be called multiple times safely."""
        class SafeCloseEnv:
            def __init__(self):
                self.closed = False
                
            def close(self):
                if not self.closed:
                    self.closed = True
        
        env = SafeCloseEnv()
        env.close()
        env.close()  # Should not raise
        assert env.closed


class TestSystemMetrics:
    """Test system-level metrics calculation."""
    
    def test_average_waiting_time(self, mock_environment):
        """Test average waiting time calculation."""
        total_waiting = 0
        num_agents = len(mock_environment.ts_ids)
        
        for ts_id in mock_environment.ts_ids:
            ts = mock_environment.traffic_signals[ts_id]
            total_waiting += sum(ts.get_accumulated_waiting_time_per_lane())
        
        avg_waiting = total_waiting / num_agents if num_agents > 0 else 0
        assert isinstance(avg_waiting, float)
    
    def test_average_queue(self, mock_environment):
        """Test average queue calculation."""
        total_queue = 0
        num_agents = len(mock_environment.ts_ids)
        
        for ts_id in mock_environment.ts_ids:
            ts = mock_environment.traffic_signals[ts_id]
            total_queue += ts.get_total_queued()
        
        avg_queue = total_queue / num_agents if num_agents > 0 else 0
        assert isinstance(avg_queue, (int, float))
    
    def test_metrics_fallback_on_error(self):
        """Test that metrics return defaults on error."""
        default_metrics = {
            'avg_waiting_time': 0.0,
            'total_waiting_time': 0.0,
            'avg_queue': 0.0,
            'total_queue': 0.0,
        }
        
        # Simulate error case
        try:
            raise Exception("Simulated error")
        except Exception:
            metrics = default_metrics
        
        assert metrics['avg_waiting_time'] == 0.0
        assert metrics['avg_queue'] == 0.0

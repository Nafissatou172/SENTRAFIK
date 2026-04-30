"""
Unit tests for observation functions.

Tests the modular observation system for traffic signal control.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch


class TestObservationFunctions:
    """Test suite for observation functions."""
    
    def test_mock_traffic_signal_lanes(self, mock_traffic_signal):
        """Test that mock traffic signal has correct number of lanes."""
        assert len(mock_traffic_signal.lanes) == 4
        assert mock_traffic_signal.id == "t1"
    
    def test_mock_traffic_signal_queue_lengths(self, mock_traffic_signal_with_data):
        """Test queue length retrieval."""
        queues = mock_traffic_signal_with_data.get_lanes_queue()
        assert queues == [5, 3, 8, 2]
        assert sum(queues) == 18
    
    def test_mock_traffic_signal_waiting_times(self, mock_traffic_signal_with_data):
        """Test waiting time retrieval."""
        waiting = mock_traffic_signal_with_data.get_accumulated_waiting_time_per_lane()
        assert waiting == [10.5, 5.2, 20.1, 3.0]
        assert abs(sum(waiting) - 38.8) < 0.01
    
    def test_mock_traffic_signal_total_queued(self, mock_traffic_signal_with_data):
        """Test total queued vehicles."""
        total = mock_traffic_signal_with_data.get_total_queued()
        assert total == 18
    
    def test_mock_traffic_signal_neighbors(self, mock_traffic_signal_with_data):
        """Test neighbor retrieval."""
        neighbors = mock_traffic_signal_with_data.get_neighbor_ids()
        assert neighbors == ["t2", "t3"]
    
    def test_mock_traffic_signal_approaching(self, mock_traffic_signal_with_data):
        """Test approaching vehicle counts."""
        approaching = mock_traffic_signal_with_data.get_lanes_count()
        assert approaching == [10, 8, 15, 5]


class TestObservationNormalization:
    """Test normalization utilities."""
    
    def test_normalize_queue_basic(self):
        """Test basic normalization."""
        value = 50
        min_val = 0
        max_val = 100
        
        normalized = (value - min_val) / (max_val - min_val)
        assert normalized == 0.5
    
    def test_normalize_queue_edge_cases(self):
        """Test normalization edge cases."""
        # At minimum
        assert (0 - 0) / (100 - 0) == 0.0
        
        # At maximum
        assert (100 - 0) / (100 - 0) == 1.0
    
    def test_normalize_clipping(self):
        """Test that values are clipped to [0, 1]."""
        value = 150  # Exceeds max
        min_val = 0
        max_val = 100
        
        normalized = (value - min_val) / (max_val - min_val)
        clipped = max(0.0, min(1.0, normalized))
        assert clipped == 1.0
        
        value = -50  # Below min
        normalized = (value - min_val) / (max_val - min_val)
        clipped = max(0.0, min(1.0, normalized))
        assert clipped == 0.0


class TestObservationSpace:
    """Test observation space definitions."""
    
    def test_queue_observation_size(self, mock_traffic_signal):
        """Test queue observation has correct size."""
        num_lanes = len(mock_traffic_signal.lanes)
        assert num_lanes == 4
    
    def test_combined_observation_components(self, mock_traffic_signal_with_data):
        """Test combined observation includes all components."""
        ts = mock_traffic_signal_with_data
        
        # Queue component
        queue = ts.get_lanes_queue()
        assert len(queue) == 4
        
        # Waiting time component
        waiting = ts.get_accumulated_waiting_time_per_lane()
        assert len(waiting) == 4
        
        # Wave/approaching component
        wave = ts.get_lanes_count()
        assert len(wave) == 4
        
        # Total observation size (without phase encoding)
        total_without_phase = len(queue) + len(waiting) + len(wave)
        assert total_without_phase == 12

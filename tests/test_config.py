"""
Unit tests for configuration loading.

Tests the config_loader module functionality.
"""

import pytest
import os
import tempfile
from pathlib import Path


class TestConfigLoading:
    """Test configuration file loading."""
    
    def test_default_config_exists(self):
        """Test that default configuration is available."""
        from modules.config_loader import DEFAULT_CONFIG
        
        assert 'environment' in DEFAULT_CONFIG
        assert 'training' in DEFAULT_CONFIG
        assert 'logging' in DEFAULT_CONFIG
    
    def test_default_config_values(self):
        """Test default configuration values."""
        from modules.config_loader import DEFAULT_CONFIG
        
        assert DEFAULT_CONFIG['environment']['delta_time'] == 10
        assert DEFAULT_CONFIG['training']['learning_rate'] == 0.0003
        assert DEFAULT_CONFIG['logging']['level'] == 'INFO'
    
    def test_deep_merge(self):
        """Test deep merge of dictionaries."""
        from modules.config_loader import deep_merge
        
        base = {'a': 1, 'b': {'c': 2, 'd': 3}}
        override = {'b': {'c': 5}, 'e': 6}
        
        result = deep_merge(base, override)
        
        assert result['a'] == 1
        assert result['b']['c'] == 5  # Overridden
        assert result['b']['d'] == 3  # Preserved
        assert result['e'] == 6       # Added


class TestEnvironmentOverrides:
    """Test environment variable overrides."""
    
    def test_parse_bool_true(self):
        """Test parsing boolean true values."""
        from modules.config_loader import _parse_env_value
        
        assert _parse_env_value('true') is True
        assert _parse_env_value('True') is True
        assert _parse_env_value('yes') is True
        assert _parse_env_value('1') is True
    
    def test_parse_bool_false(self):
        """Test parsing boolean false values."""
        from modules.config_loader import _parse_env_value
        
        assert _parse_env_value('false') is False
        assert _parse_env_value('False') is False
        assert _parse_env_value('no') is False
        assert _parse_env_value('0') is False
    
    def test_parse_int(self):
        """Test parsing integer values."""
        from modules.config_loader import _parse_env_value
        
        assert _parse_env_value('42') == 42
        assert _parse_env_value('-10') == -10
    
    def test_parse_float(self):
        """Test parsing float values."""
        from modules.config_loader import _parse_env_value
        
        assert _parse_env_value('3.14') == 3.14
        assert _parse_env_value('0.001') == 0.001
    
    def test_parse_string(self):
        """Test parsing string values."""
        from modules.config_loader import _parse_env_value
        
        assert _parse_env_value('hello') == 'hello'
        assert _parse_env_value('path/to/file') == 'path/to/file'


class TestDataclassConfigs:
    """Test configuration dataclasses."""
    
    def test_environment_config_from_dict(self, sample_config):
        """Test EnvironmentConfig dataclass creation."""
        from modules.config_loader import EnvironmentConfig
        
        config = EnvironmentConfig.from_dict(sample_config)
        
        assert config.net_file == 'test_network.net.xml'
        assert config.delta_time == 10
        assert config.use_gui is False
    
    def test_training_config_from_dict(self, sample_config):
        """Test TrainingConfig dataclass creation."""
        from modules.config_loader import TrainingConfig
        
        config = TrainingConfig.from_dict(sample_config)
        
        assert config.learning_rate == 0.0003
        assert config.batch_size == 256
    
    def test_config_defaults(self):
        """Test that dataclasses have proper defaults."""
        from modules.config_loader import EnvironmentConfig, TrainingConfig
        
        env_config = EnvironmentConfig()
        assert env_config.delta_time == 10
        
        train_config = TrainingConfig()
        assert train_config.gamma == 0.99

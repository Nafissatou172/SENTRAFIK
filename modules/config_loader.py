"""
Configuration Loader for Oraban Traffic Signal Control Project.

Provides utilities to load and validate configuration from:
1. YAML configuration file
2. Environment variable overrides (prefixed with ORABAN_)
3. Default values fallback
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


# Default configuration values
DEFAULT_CONFIG = {
    'environment': {
        'net_file': 'configuration_files/grid4x4.net.xml',
        'route_file_emergency': 'configuration_files/grid4x4_realistic.rou.xml',
        'route_file_no_emergency': 'configuration_files/grid4x4_no_emergency.rou.xml',
        'delta_time': 10,
        'yellow_time': 5,
        'min_green': 10,
        'max_green': 50,
        'num_seconds': 1800,
        'sumo_warnings': False,
        'use_gui': False,
    },
    'training': {
        'num_parallel_envs': 4,
        'learning_rate': 0.0003,
        'gamma': 0.99,
        'tau': 0.005,
        'buffer_size': 100000,
        'batch_size': 256,
        'epsilon_start': 1.0,
        'epsilon_min': 0.01,
        'epsilon_decay': 0.994,
        'reward_scale': 0.01,
        'gradient_clip': 10.0,
        'update_target_every': 1000,
        'max_episodes': 2500,
        'max_steps_per_episode': 1800,
        'eval_frequency': 50,
        'patience': 200,
        'save_frequency': 100,
        'checkpoint_dir': 'models_custom_multienv',
    },
    'logging': {
        'level': 'INFO',
        'log_dir': 'logs',
        'log_to_file': True,
        'log_to_console': True,
        'max_file_size_mb': 10,
        'backup_count': 5,
        'use_colors': True,
    },
    'tensorboard': {
        'enabled': True,
        'log_dir': 'logs_custom_multienv',
    },
    'observation': {
        'include_queue': True,
        'include_waiting_time': True,
        'include_wave': True,
        'include_phase': True,
        'include_emergency': True,
        'include_neighbors': True,
        'neighbor_distance': 1,
        'normalize': True,
    },
    'reward': {
        'queue_weight': 0.5,
        'waiting_time_weight': 0.3,
        'emergency_weight': 0.2,
        'normalize': False,
    },
}


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries, with override taking precedence.
    
    Args:
        base: Base dictionary
        override: Dictionary with values to override
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def apply_env_overrides(config: Dict) -> Dict:
    """
    Apply environment variable overrides to config.
    
    Environment variables should be prefixed with ORABAN_ and use double underscores
    for nested keys. For example:
    - ORABAN_LOGGING__LEVEL=DEBUG -> config['logging']['level'] = 'DEBUG'
    - ORABAN_TRAINING__LEARNING_RATE=0.001 -> config['training']['learning_rate'] = 0.001
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration with environment overrides applied
    """
    prefix = 'ORABAN_'
    
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        
        # Remove prefix and split by double underscore
        key_path = env_key[len(prefix):].lower().split('__')
        
        # Navigate to the nested location
        current = config
        for key in key_path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the value with type inference
        final_key = key_path[-1]
        current[final_key] = _parse_env_value(env_value)
    
    return config


def _parse_env_value(value: str) -> Any:
    """Parse environment variable value to appropriate type."""
    # Boolean
    if value.lower() in ('true', 'yes', '1'):
        return True
    if value.lower() in ('false', 'no', '0'):
        return False
    
    # Integer
    try:
        return int(value)
    except ValueError:
        pass
    
    # Float
    try:
        return float(value)
    except ValueError:
        pass
    
    # String
    return value


def load_config(config_path: Optional[str] = None) -> Dict:
    """
    Load configuration from file with defaults and environment overrides.
    
    Priority (highest to lowest):
    1. Environment variables (ORABAN_*)
    2. Config file values
    3. Default values
    
    Args:
        config_path: Path to YAML config file. If None, searches for config.yaml
                    in the current directory and parent directories.
                    
    Returns:
        Complete configuration dictionary
    """
    # Start with defaults
    config = DEFAULT_CONFIG.copy()
    
    # Find config file
    if config_path is None:
        config_path = _find_config_file()
    
    # Load from file if exists
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            file_config = yaml.safe_load(f) or {}
        config = deep_merge(config, file_config)
    
    # Apply environment overrides
    config = apply_env_overrides(config)
    
    return config


def _find_config_file() -> Optional[str]:
    """Search for config.yaml in current and parent directories."""
    current = Path.cwd()
    
    for _ in range(5):  # Search up to 5 levels
        config_path = current / 'config.yaml'
        if config_path.exists():
            return str(config_path)
        
        parent = current.parent
        if parent == current:  # Reached root
            break
        current = parent
    
    return None


@dataclass
class EnvironmentConfig:
    """Environment configuration dataclass."""
    net_file: str = 'configuration_files/grid4x4.net.xml'
    route_file_emergency: str = 'configuration_files/grid4x4_realistic.rou.xml'
    route_file_no_emergency: str = 'configuration_files/grid4x4_no_emergency.rou.xml'
    delta_time: int = 10
    yellow_time: int = 5
    min_green: int = 10
    max_green: int = 50
    num_seconds: int = 1800
    sumo_warnings: bool = False
    use_gui: bool = False
    
    @classmethod
    def from_dict(cls, config: Dict) -> 'EnvironmentConfig':
        env_config = config.get('environment', {})
        return cls(**{k: v for k, v in env_config.items() if k in cls.__dataclass_fields__})


@dataclass
class TrainingConfig:
    """Training configuration dataclass."""
    num_parallel_envs: int = 4
    learning_rate: float = 0.0003
    gamma: float = 0.99
    tau: float = 0.005
    buffer_size: int = 100000
    batch_size: int = 256
    epsilon_start: float = 1.0
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.994
    reward_scale: float = 0.01
    gradient_clip: float = 10.0
    update_target_every: int = 1000
    max_episodes: int = 2500
    max_steps_per_episode: int = 1800
    eval_frequency: int = 50
    patience: int = 200
    save_frequency: int = 100
    checkpoint_dir: str = 'models_custom_multienv'
    
    @classmethod
    def from_dict(cls, config: Dict) -> 'TrainingConfig':
        train_config = config.get('training', {})
        return cls(**{k: v for k, v in train_config.items() if k in cls.__dataclass_fields__})


# Global config instance (lazy loaded)
_config: Optional[Dict] = None


def get_config() -> Dict:
    """Get the global configuration, loading if necessary."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_environment_config() -> EnvironmentConfig:
    """Get environment configuration as dataclass."""
    return EnvironmentConfig.from_dict(get_config())


def get_training_config() -> TrainingConfig:
    """Get training configuration as dataclass."""
    return TrainingConfig.from_dict(get_config())

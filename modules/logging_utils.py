"""
Logging Utilities for Co-DQL Training.

This module provides comprehensive logging functionality for the Co-DQL
multi-agent reinforcement learning system, including:
- Console logging with configurable verbosity
- File-based logging for metrics
- Optional TensorBoard support

Requirements: 10.1, 10.2, 10.3, 10.4

Author: Research Project
Date: 2025
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import numpy as np


@dataclass
class EpisodeMetrics:
    """
    Metrics collected during an episode.
    
    Requirements: 10.1, 10.2
    """
    episode: int
    total_reward: float
    mean_reward: float
    total_waiting_time: float = 0.0
    avg_queue_length: float = 0.0
    avg_loss: float = 0.0
    epsilon: float = 0.0
    steps: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


@dataclass
class TrainingMetrics:
    """
    Aggregated training metrics across episodes.
    
    Requirements: 10.2
    """
    q_value_mean: float = 0.0
    q_value_std: float = 0.0
    q_value_max: float = 0.0
    q_value_min: float = 0.0
    loss_mean: float = 0.0
    loss_std: float = 0.0
    exploration_rate: float = 0.0
    buffer_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


class CoDQLLogger:
    """
    Comprehensive logger for Co-DQL training.
    
    Provides:
    - Console logging with configurable verbosity (DEBUG, INFO, WARNING, ERROR)
    - File-based logging for metrics (JSON format)
    - Optional TensorBoard support for visualization
    
    Requirements: 10.1, 10.2, 10.3, 10.4
    """
    
    # Log level mapping
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    def __init__(
        self,
        name: str = "CoDQL",
        log_level: str = "INFO",
        log_file: Optional[str] = "training.log",
        metrics_file: Optional[str] = "metrics.json",
        use_tensorboard: bool = False,
        tensorboard_dir: str = "runs",
        console_output: bool = True
    ):
        """
        Initialize the CoDQL logger.
        
        Args:
            name: Logger name
            log_level: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (None to disable file logging)
            metrics_file: Path to metrics JSON file (None to disable)
            use_tensorboard: Whether to enable TensorBoard logging
            tensorboard_dir: Directory for TensorBoard logs
            console_output: Whether to output to console
            
        Requirements: 10.3
        """
        self.name = name
        self.log_level = log_level.upper()
        self.log_file = log_file
        self.metrics_file = metrics_file
        self.use_tensorboard = use_tensorboard
        self.tensorboard_dir = tensorboard_dir
        self.console_output = console_output
        
        # Set up Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.LOG_LEVELS.get(self.log_level, logging.INFO))
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler - Requirements 10.3
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.LOG_LEVELS.get(self.log_level, logging.INFO))
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler - Requirements 10.3
        if log_file:
            # Ensure directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setLevel(logging.DEBUG)  # Log everything to file
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Metrics storage
        self.episode_metrics: List[EpisodeMetrics] = []
        self.training_metrics: List[TrainingMetrics] = []
        
        # TensorBoard writer - Requirements 10.4
        self.writer = None
        if use_tensorboard:
            self._setup_tensorboard()
        
        # Ensure metrics directory exists
        if metrics_file:
            metrics_dir = os.path.dirname(metrics_file)
            if metrics_dir:
                os.makedirs(metrics_dir, exist_ok=True)
    
    def _setup_tensorboard(self) -> None:
        """Set up TensorBoard writer."""
        try:
            from torch.utils.tensorboard import SummaryWriter
            
            # Create unique run directory with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            run_dir = os.path.join(self.tensorboard_dir, f"{self.name}_{timestamp}")
            os.makedirs(run_dir, exist_ok=True)
            
            self.writer = SummaryWriter(run_dir)
            self.logger.info(f"TensorBoard logging enabled at {run_dir}")
        except ImportError:
            self.logger.warning(
                "TensorBoard not available. Install with: pip install tensorboard"
            )
            self.use_tensorboard = False
    
    def set_level(self, level: str) -> None:
        """
        Set logging verbosity level.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level = level.upper()
        if level in self.LOG_LEVELS:
            self.log_level = level
            self.logger.setLevel(self.LOG_LEVELS[level])
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    handler.setLevel(self.LOG_LEVELS[level])
    
    # Standard logging methods
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)

    
    def log_episode(
        self,
        episode: int,
        total_reward: float,
        mean_reward: float,
        total_waiting_time: float = 0.0,
        avg_queue_length: float = 0.0,
        avg_loss: float = 0.0,
        epsilon: float = 0.0,
        steps: int = 0
    ) -> EpisodeMetrics:
        """
        Log episode completion metrics.
        
        Args:
            episode: Episode number
            total_reward: Total episode reward
            mean_reward: Mean reward per agent
            total_waiting_time: Total waiting time in episode
            avg_queue_length: Average queue length
            avg_loss: Average training loss
            epsilon: Current exploration rate
            steps: Number of steps in episode
            
        Returns:
            EpisodeMetrics object
            
        Requirements: 10.1
        """
        metrics = EpisodeMetrics(
            episode=episode,
            total_reward=total_reward,
            mean_reward=mean_reward,
            total_waiting_time=total_waiting_time,
            avg_queue_length=avg_queue_length,
            avg_loss=avg_loss,
            epsilon=epsilon,
            steps=steps
        )
        
        self.episode_metrics.append(metrics)
        
        # Log to console/file
        self.info(
            f"Episode {episode}: "
            f"reward={total_reward:.2f}, "
            f"mean_reward={mean_reward:.2f}, "
            f"loss={avg_loss:.4f}, "
            f"steps={steps}, "
            f"epsilon={epsilon:.4f}"
        )
        
        # Log to TensorBoard - Requirements 10.4
        if self.writer is not None:
            self.writer.add_scalar('Episode/TotalReward', total_reward, episode)
            self.writer.add_scalar('Episode/MeanReward', mean_reward, episode)
            self.writer.add_scalar('Episode/Loss', avg_loss, episode)
            self.writer.add_scalar('Episode/Steps', steps, episode)
            self.writer.add_scalar('Episode/Epsilon', epsilon, episode)
            self.writer.add_scalar('Episode/WaitingTime', total_waiting_time, episode)
            self.writer.add_scalar('Episode/QueueLength', avg_queue_length, episode)
        
        return metrics
    
    def log_training_metrics(
        self,
        step: int,
        q_values: Optional[np.ndarray] = None,
        loss: Optional[float] = None,
        exploration_rate: float = 0.0,
        buffer_size: int = 0
    ) -> TrainingMetrics:
        """
        Log training progress metrics.
        
        Args:
            step: Training step number
            q_values: Q-values array for statistics
            loss: Current loss value
            exploration_rate: Current exploration rate
            buffer_size: Current replay buffer size
            
        Returns:
            TrainingMetrics object
            
        Requirements: 10.2
        """
        metrics = TrainingMetrics(
            exploration_rate=exploration_rate,
            buffer_size=buffer_size
        )
        
        if q_values is not None:
            metrics.q_value_mean = float(np.mean(q_values))
            metrics.q_value_std = float(np.std(q_values))
            metrics.q_value_max = float(np.max(q_values))
            metrics.q_value_min = float(np.min(q_values))
        
        if loss is not None:
            metrics.loss_mean = loss
        
        self.training_metrics.append(metrics)
        
        # Log to TensorBoard - Requirements 10.4
        if self.writer is not None:
            if q_values is not None:
                self.writer.add_scalar('Training/Q_Mean', metrics.q_value_mean, step)
                self.writer.add_scalar('Training/Q_Std', metrics.q_value_std, step)
                self.writer.add_scalar('Training/Q_Max', metrics.q_value_max, step)
                self.writer.add_scalar('Training/Q_Min', metrics.q_value_min, step)
            if loss is not None:
                self.writer.add_scalar('Training/Loss', loss, step)
            self.writer.add_scalar('Training/ExplorationRate', exploration_rate, step)
            self.writer.add_scalar('Training/BufferSize', buffer_size, step)
        
        return metrics
    
    def log_evaluation(
        self,
        episode: int,
        mean_reward: float,
        std_reward: float,
        min_reward: float,
        max_reward: float,
        mean_steps: float
    ) -> None:
        """
        Log evaluation results.
        
        Args:
            episode: Episode number when evaluation was performed
            mean_reward: Mean evaluation reward
            std_reward: Standard deviation of rewards
            min_reward: Minimum reward
            max_reward: Maximum reward
            mean_steps: Mean steps per episode
        """
        self.info(
            f"Evaluation at episode {episode}: "
            f"mean_reward={mean_reward:.2f} ± {std_reward:.2f}, "
            f"min={min_reward:.2f}, max={max_reward:.2f}, "
            f"mean_steps={mean_steps:.1f}"
        )
        
        # Log to TensorBoard
        if self.writer is not None:
            self.writer.add_scalar('Evaluation/MeanReward', mean_reward, episode)
            self.writer.add_scalar('Evaluation/StdReward', std_reward, episode)
            self.writer.add_scalar('Evaluation/MinReward', min_reward, episode)
            self.writer.add_scalar('Evaluation/MaxReward', max_reward, episode)
            self.writer.add_scalar('Evaluation/MeanSteps', mean_steps, episode)
    
    def log_checkpoint(self, episode: int, path: str) -> None:
        """Log checkpoint save."""
        self.info(f"Checkpoint saved at episode {episode}: {path}")
    
    def log_best_model(self, episode: int, reward: float, path: str) -> None:
        """Log best model save."""
        self.info(f"New best model at episode {episode} with reward {reward:.2f}: {path}")
    
    def save_metrics(self, filepath: Optional[str] = None) -> None:
        """
        Save all metrics to JSON file.
        
        Args:
            filepath: Path to save metrics (uses default if None)
            
        Requirements: 10.3
        """
        filepath = filepath or self.metrics_file
        if filepath is None:
            return
        
        # Ensure directory exists
        metrics_dir = os.path.dirname(filepath)
        if metrics_dir:
            os.makedirs(metrics_dir, exist_ok=True)
        
        metrics_data = {
            'episode_metrics': [m.to_dict() for m in self.episode_metrics],
            'training_metrics': [m.to_dict() for m in self.training_metrics],
            'metadata': {
                'name': self.name,
                'log_level': self.log_level,
                'total_episodes': len(self.episode_metrics),
                'saved_at': datetime.now().isoformat()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        self.debug(f"Metrics saved to {filepath}")
    
    def load_metrics(self, filepath: str) -> Dict[str, Any]:
        """
        Load metrics from JSON file.
        
        Args:
            filepath: Path to metrics file
            
        Returns:
            Dictionary with loaded metrics
        """
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of logged metrics.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.episode_metrics:
            return {}
        
        rewards = [m.total_reward for m in self.episode_metrics]
        losses = [m.avg_loss for m in self.episode_metrics if m.avg_loss > 0]
        
        return {
            'total_episodes': len(self.episode_metrics),
            'reward_mean': np.mean(rewards),
            'reward_std': np.std(rewards),
            'reward_max': np.max(rewards),
            'reward_min': np.min(rewards),
            'loss_mean': np.mean(losses) if losses else 0.0,
            'loss_std': np.std(losses) if losses else 0.0,
            'final_epsilon': self.episode_metrics[-1].epsilon if self.episode_metrics else 0.0
        }
    
    def close(self) -> None:
        """
        Close logger and save final metrics.
        
        Should be called at the end of training.
        """
        # Save metrics
        if self.metrics_file:
            self.save_metrics()
        
        # Close TensorBoard writer
        if self.writer is not None:
            self.writer.close()
            self.writer = None
        
        # Log summary
        summary = self.get_summary()
        if summary:
            self.info(f"Training complete. Summary: {summary}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


def create_logger(
    name: str = "CoDQL",
    config: Optional[Any] = None,
    **kwargs
) -> CoDQLLogger:
    """
    Factory function to create a CoDQL logger.
    
    Args:
        name: Logger name
        config: CoDQLConfig object (optional)
        **kwargs: Additional logger arguments
        
    Returns:
        CoDQLLogger instance
    """
    if config is not None:
        # Extract logging config from CoDQLConfig
        return CoDQLLogger(
            name=name,
            log_level=getattr(config, 'log_level', 'INFO'),
            log_file=getattr(config, 'log_file', 'training.log'),
            use_tensorboard=getattr(config, 'use_tensorboard', False),
            tensorboard_dir=getattr(config, 'tensorboard_dir', 'runs'),
            **kwargs
        )
    else:
        return CoDQLLogger(name=name, **kwargs)


# Convenience function for quick setup
def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = "training.log",
    use_tensorboard: bool = False
) -> CoDQLLogger:
    """
    Quick setup for logging.
    
    Args:
        log_level: Logging verbosity
        log_file: Path to log file
        use_tensorboard: Whether to enable TensorBoard
        
    Returns:
        Configured CoDQLLogger instance
    """
    return CoDQLLogger(
        name="CoDQL",
        log_level=log_level,
        log_file=log_file,
        use_tensorboard=use_tensorboard
    )

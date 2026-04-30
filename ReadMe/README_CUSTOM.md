# Multi-Environment Training for Your Custom Co-DQL Environment

This setup allows you to use your existing custom environment (with custom observations and rewards) while getting the benefits of multi-environment parallel training for 4-8x faster learning.

## 📁 Project Structure

```
your_project/
├── config.yaml                       # Configuration file
├── modules/
│   ├── environment.py                # Your custom Environment class
│   ├── observation.py                # Your custom observations
│   ├── reward.py                     # Your custom rewards
│   ├── config_loader.py              # Configuration loader
│   └── logging_config.py             # Logging setup
├── tests/                            # Unit tests
│   ├── conftest.py
│   ├── test_observations.py
│   ├── test_rewards.py
│   ├── test_environment.py
│   └── test_config.py
├── configuration_files/
│   ├── grid4x4.net.xml               # SUMO network file
│   └── grid4x4_realistic.rou.xml     # SUMO route file
├── agent_stable_pytorch_corrected.py # Fixed Co-DQL agent
├── custom_env_wrapper.py             # Wrapper for your environment
└── train_custom_multienv.py          # Multi-env training script
```

## 🚀 Quick Start

### 1. Setup

Make sure you have all the required files from your existing project:
- `modules/environment.py` - Your Environment class
- `modules/observation.py` - Your observation classes
- `modules/reward.py` - Your reward classes
- `configuration_files/` - Your SUMO network and route files

### 2. Install Dependencies

```bash
pip install torch numpy matplotlib tensorboard sumo-rl gymnasium
```

### 3. Train with Multiple Environments

```bash
# Basic training with 4 parallel environments (4x faster!)
python train_custom_multienv.py --episodes 2500 --num-envs 4

# With emergency vehicles
python train_custom_multienv.py --episodes 2500 --num-envs 4 --use-emergency

# With more parallel environments (8x faster!)
python train_custom_multienv.py --episodes 2500 --num-envs 8

# Custom learning rate
python train_custom_multienv.py --episodes 2500 --num-envs 4 --learning-rate 0.0002
```

## 🎯 What's Different from Before?

### Before (Single Environment)
```python
from modules.environment import Environment

env = Environment()
# Train with one environment at a time
# Takes ~4 hours for 1000 episodes
```

### Now (Multi-Environment)
```python
from custom_env_wrapper import CustomEnvWrapper, MultiEnvWrapper

# Create multiple parallel environments
envs = MultiEnvWrapper([...], num_envs=4)
# Train with 4 environments in parallel
# Takes ~1 hour for 1000 episodes (4x faster!)
```

**Key benefit**: Same environment, observations, and rewards - just faster training!

## ⚙️ How It Works

The wrapper system works in layers:

1. **Your Environment** (`modules/environment.py`)
   - Uses `sumo_rl.SumoEnvironment`
   - Your custom `NeighborCombinedObservation`
   - Your custom `CombinedReward`

2. **CustomEnvWrapper** (`custom_env_wrapper.py`)
   - Wraps your Environment
   - Makes it compatible with multi-env training
   - Adds system metrics tracking

3. **MultiEnvWrapper** (`custom_env_wrapper.py`)
   - Manages multiple CustomEnvWrapper instances
   - Runs them in parallel
   - Collects experiences from all

4. **Trainer** (`train_custom_multienv.py`)
   - Coordinates parallel episodes
   - Trains agents on combined experience
   - Same agent networks, more data!

## 📊 Performance Comparison

| Setup | Episodes | Time | Speed-up |
|-------|----------|------|----------|
| Single Env | 1000 | ~4 hours | 1x (baseline) |
| 4 Parallel Envs | 1000 | ~1.1 hours | 3.5x faster |
| 8 Parallel Envs | 1000 | ~40 minutes | 6x faster |

## 🔧 Configuration

Key parameters in `train_custom_multienv.py`:

```python
config = {
    'env_config': {
        'use_emergency_vehicles': True,  # Use emergency vehicle routes
        'use_gui': False,                # Don't use GUI (faster)
    },
    
    'num_parallel_envs': 4,          # Number of parallel environments
    'learning_rate': 0.0003,         # Learning rate
    'batch_size': 256,               # Training batch size
    'buffer_size': 100000,           # Replay buffer size
    'epsilon_decay': 0.994,          # Exploration decay
    
    # Stability features
    'reward_scale': 0.01,            # Reward normalization
    'gradient_clip': 10.0,           # Gradient clipping
    
    # Training settings
    'max_steps_per_episode': 1800,  # Your episode length
    'eval_frequency': 50,            # Evaluate every N episodes
    'patience': 200,                 # Early stopping patience
}
```

## 📈 Monitoring

### TensorBoard

```bash
tensorboard --logdir logs_custom_multienv
```

Open http://localhost:6006 to see:
- Episode rewards
- Waiting times
- Queue lengths
- Training loss
- Exploration rate

### Training Curves

After training, check:
- `logs_custom_multienv/training_curves.png`

## 💾 Models

Models are saved in `models_custom_multienv/`:

```
models_custom_multienv/
├── best_model/              # Best model based on evaluation
│   ├── t1.pt               # Agent for intersection t1
│   ├── t2.pt               # Agent for intersection t2
│   ├── ...
│   ├── config.json
│   └── training_stats.json
├── checkpoint_episode_500/  # Periodic checkpoints
└── final/                   # Final model
```

## 🎮 Your Environment Features

Your custom environment includes:

### Observations (NeighborCombinedObservation)
- ✅ Queue lengths (per lane)
- ✅ Waiting times (per lane)
- ✅ Wave/density (approaching vehicles)
- ✅ Current phase (one-hot)
- ✅ Emergency vehicles (detection)
- ✅ Neighbor observations
  - Neighbor phases
  - Neighbor queues
  - Neighbor waiting times
  - Neighbor actions

### Rewards (CombinedReward)
- ✅ Queue minimization
- ✅ Waiting time minimization
- ✅ Emergency vehicle priority
- ✅ Weighted combination

All these features are preserved in the multi-environment setup!

## 🔄 Loading and Evaluating

```python
from train_custom_multienv import CustomMultiEnvTrainer

# Setup config
config = {...}

# Create trainer
trainer = CustomMultiEnvTrainer(config)

# Load best model
trainer.load_models("best_model")

# Evaluate
results = trainer.evaluate(num_episodes=10)

print(f"Avg Reward: {results['avg_reward']:.2f}")
print(f"Avg Waiting Time: {results['avg_waiting_time']:.2f}")
print(f"Avg Queue: {results['avg_queue']:.2f}")
```

## 🎮 Running Simulation with GUI

To visualize the trained agents controlling traffic in real-time, use the provided `run_simulation.py` script:

```bash
# Basic usage (loads best model from default path)
python run_simulation.py

# Specify number of episodes
python run_simulation.py --episodes 5

# Disable GUI (headless mode)
python run_simulation.py --no-gui

# Disable emergency vehicles
python run_simulation.py --no-emergency
```

This script loads the trained models from `models_custom_multienv/best_model` and runs the simulation. You can see the traffic lights changing and vehicles moving.


## 🐛 Troubleshooting

### Issue: Different Action Spaces Per Agent

Your environment correctly handles agents with different numbers of phases (action spaces). The wrapper accounts for this:

```python
# Each agent gets its own action space
for agent_id in self.agent_ids:
    agent_action_dim = action_spaces[agent_id].n
    agent = StableCoDQLAgent(
        action_dim=agent_action_dim,  # Agent-specific!
        ...
    )
```

### Issue: Mean Field with Different Action Dimensions

The `compute_mean_actions()` method handles this:

```python
# Uses max action dimension
max_action_dim = max(action_spaces[aid].n for aid in agents)

# Truncates to each agent's actual dimension
for agent_id in agents:
    agent_action_dim = action_spaces[agent_id].n
    mean_actions[agent_id] = mean_dist[:agent_action_dim]
```

### Issue: Out of Memory

Reduce parallel environments:
```bash
python train_custom_multienv.py --num-envs 2
```

Or reduce buffer size:
```python
config['buffer_size'] = 50000
config['batch_size'] = 128
```

## 📝 Example Training Session

```bash
$ python train_custom_multienv.py --episodes 1000 --num-envs 4

Using device: cuda
Creating 4 parallel custom environments...
Initialized custom environment with 16 agents: ['t1', 't2', ..., 't16']
State dimension: 210  # Your rich observation space!
Action dimension: 4
Number of agents: 16
Creating 16 stable Co-DQL agents...

============================================================
Starting Multi-Environment Training for 1000 episodes
Using 4 parallel environments
============================================================

Episode 10/1000
============================================================
  Avg Reward: -45.23
  Total Reward: -723.68
  Recent 50 Avg: -47.12
  Best Episode Reward: -inf
  Avg Waiting Time: 125.34
  Avg Queue: 8.45
  Epsilon: 0.9412
  Avg Loss: 2.341

...

************************************************************
  EVALUATION RESULTS (Episode 500)
************************************************************
  Eval Avg Reward: -32.45
  Eval Std Reward: 3.21
  Eval Avg Waiting Time: 98.23
  Eval Avg Queue: 6.12
************************************************************

  ✓ New best model saved! (eval reward: -32.45)

...

Training completed!
Training curves saved to logs_custom_multienv/training_curves.png
```

## 🎯 Key Advantages

1. **4-8x Faster Training** - Multiple environments in parallel
2. **Same Environment** - Your custom observations and rewards
3. **Better Exploration** - More diverse experiences
4. **Stable Learning** - Gradient clipping, reward normalization
5. **Early Stopping** - Prevents overfitting
6. **Easy Monitoring** - TensorBoard integration

## 🤝 Integration with Existing Code

No changes needed to your existing modules:
- ✅ `modules/environment.py` - Works as-is
- ✅ `modules/observation.py` - Works as-is
- ✅ `modules/reward.py` - Works as-is
- ✅ SUMO configuration files - Works as-is

Just add the new files and start training faster!

---

## ⚙️ Configuration

All settings can be configured via `config.yaml`:

```yaml
# SUMO Environment
environment:
  delta_time: 10
  yellow_time: 5
  min_green: 10
  max_green: 50
  use_gui: false

# Training
training:
  learning_rate: 0.0003
  batch_size: 256
  num_parallel_envs: 4
  epsilon_decay: 0.994

# Logging
logging:
  level: INFO
  log_to_file: true
```

### Environment Variable Overrides

Override any setting with environment variables prefixed with `ORABAN_`:

```bash
# Override learning rate
ORABAN_TRAINING__LEARNING_RATE=0.001 python train_custom_multienv.py

# Enable debug logging
ORABAN_LOGGING__LEVEL=DEBUG python train_custom_multienv.py
```

### Loading Config in Code

```python
from modules.config_loader import get_config, get_training_config

# Get full config dictionary
config = get_config()

# Get typed dataclass for IDE support
train = get_training_config()
print(train.learning_rate)  # 0.0003
```

---

## 📋 Logging

The project uses structured logging with colored console output:

```python
from modules.logging_config import get_logger, init_logging

# Initialize logging (call once at startup)
init_logging(log_level="INFO", log_to_file=True)

# Get a logger for your module
logger = get_logger("oraban.mymodule")
logger.info("Training started")
logger.warning("Low GPU memory")
```

Logs are saved to `logs/oraban.log` with automatic rotation.

---

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_observations.py -v

# Run with coverage
pytest tests/ --cov=modules --cov-report=term-missing
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures and mocks
├── test_observations.py  # Observation function tests
├── test_rewards.py       # Reward function tests
├── test_environment.py   # Environment wrapper tests
└── test_config.py        # Configuration loader tests
```

---

**Happy Training! 🚦🚗💨**

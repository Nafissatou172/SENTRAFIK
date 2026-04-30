"""
Stable Co-DQL Agent with Improved Training Stability - PyTorch Version (CORRECTED)

Key improvements:
1. Gradient clipping to prevent gradient explosion
2. Reward normalization for numerical stability
3. Learning rate scheduling
4. Improved target network update strategy
5. Better exploration strategy
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from collections import deque


class QNetwork(nn.Module):
    """
    Q-Network with improved architecture for stability.
    
    Uses:
    - Layer normalization for stable training
    - Moderate network size to prevent overfitting
    - Proper initialization
    """
    def __init__(self, input_dim):
        super(QNetwork, self).__init__()
        
        # Layer 1 with normalization
        self.fc1 = nn.Linear(input_dim, 256)
        self.ln1 = nn.LayerNorm(256)
        
        # Layer 2 with normalization
        self.fc2 = nn.Linear(256, 128)
        self.ln2 = nn.LayerNorm(128)
        
        # Layer 3
        self.fc3 = nn.Linear(128, 64)
        
        # Output layer with small initialization
        self.fc4 = nn.Linear(64, 1)
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize weights with proper scaling."""
        # He initialization for ReLU layers
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity='relu')
        nn.init.kaiming_normal_(self.fc2.weight, nonlinearity='relu')
        nn.init.kaiming_normal_(self.fc3.weight, nonlinearity='relu')
        
        # Small initialization for output layer
        nn.init.uniform_(self.fc4.weight, -0.003, 0.003)
        nn.init.uniform_(self.fc4.bias, -0.003, 0.003)
    
    def forward(self, x):
        """Forward pass."""
        x = F.relu(self.ln1(self.fc1(x)))
        x = F.relu(self.ln2(self.fc2(x)))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return x


class StableCoDQLAgentPyTorch:
    def __init__(self, state_dim, action_dim, num_actions, 
                 learning_rate=0.0003,  # Lower learning rate
                 gamma=0.99, 
                 tau=0.005,  # Faster target network updates
                 buffer_size=1000000, 
                 batch_size=256, 
                 epsilon=1.0, 
                 epsilon_min=0.01, 
                 epsilon_decay=0.994, # Faster decay
                 reward_scale=0.01,  # Scale rewards
                 gradient_clip=10.0,  # Gradient clipping
                 update_target_every=1000,  # Hard update frequency
                 device=None):
        """
        Stable Co-DQL agent with improved training stability - PyTorch version.
        
        Args:
            state_dim: Dimension of state observation
            action_dim: Dimension of action space
            num_actions: Number of discrete actions
            learning_rate: Initial learning rate (lower for stability)
            gamma: Discount factor
            tau: Soft target network update rate
            buffer_size: Replay buffer size
            batch_size: Training batch size
            epsilon: Initial exploration rate
            epsilon_min: Minimum exploration rate
            epsilon_decay: Epsilon decay rate (faster decay)
            reward_scale: Scale factor for rewards (helps with numerical stability)
            gradient_clip: Maximum gradient norm (prevents gradient explosion)
            update_target_every: Hard target network update frequency
            device: PyTorch device (cuda/cpu)
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.num_actions = num_actions
        self.gamma = gamma
        self.tau = tau
        self.batch_size = batch_size
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.reward_scale = reward_scale
        self.gradient_clip = gradient_clip
        self.update_target_every = update_target_every
        
        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = device
        
        # Training step counter
        self.training_steps = 0
        
        # Replay buffer
        self.replay_buffer = deque(maxlen=buffer_size)
        
        # Running statistics for reward normalization
        self.reward_mean = 0.0
        self.reward_std = 1.0
        self.reward_history = deque(maxlen=10000)
        
        # Build networks
        input_dim = state_dim + 2 * action_dim
        self.qa_model = QNetwork(input_dim).to(self.device)  # Q network
        self.qb_model = QNetwork(input_dim).to(self.device)  # Target Q network
        
        # Initialize target network with same weights
        self.qb_model.load_state_dict(self.qa_model.state_dict())
        self.qb_model.eval()  # Target network in eval mode
        
        # Optimizer with learning rate schedule
        self.optimizer = torch.optim.Adam(self.qa_model.parameters(), lr=learning_rate)
        self.lr_scheduler = torch.optim.lr_scheduler.StepLR(
            self.optimizer, 
            step_size=10000, 
            gamma=0.96
        )
        
        # Loss tracking
        self.loss_history = deque(maxlen=1000)

    def normalize_reward(self, reward):
        """
        Normalize reward using running statistics.
        
        This helps with numerical stability by keeping rewards in a reasonable range.
        """
        # Update running statistics
        self.reward_history.append(reward)
        
        if len(self.reward_history) > 100:
            self.reward_mean = np.mean(self.reward_history)
            self.reward_std = np.std(self.reward_history) + 1e-8
        
        # Normalize and scale
        normalized_reward = (reward - self.reward_mean) / self.reward_std
        scaled_reward = normalized_reward * self.reward_scale
        
        return scaled_reward

    def select_action(self, state, mean_action, exploration=True):
        """
        Select action using epsilon-greedy policy.
        
        Args:
            state: Current state observation
            mean_action: Mean field action distribution
            exploration: Whether to use exploration
            
        Returns:
            Selected action index
        """
        if exploration and np.random.random() < self.epsilon:
            # Random action
            action = np.random.randint(0, self.num_actions)
        else:
            # Greedy action based on Q-values
            with torch.no_grad():
                q_values = np.zeros(self.num_actions)
                for a in range(self.num_actions):
                    one_hot_a = np.zeros(self.num_actions)
                    one_hot_a[a] = 1
                    input_vec = np.concatenate([state, one_hot_a, mean_action])
                    input_tensor = torch.FloatTensor(input_vec).unsqueeze(0).to(self.device)
                    q_values[a] = self.qa_model(input_tensor).item()
                action = np.argmax(q_values)
        
        return action
    
    def decay_epsilon(self):
        """Decay epsilon after each episode."""
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            # Ensure epsilon doesn't go below minimum
            self.epsilon = max(self.epsilon, self.epsilon_min)

    def store_transition(self, state, action, reward, next_state, next_mean_action):
        """
        Store transition in replay buffer with normalized reward.
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            next_mean_action: Mean field action for next state
        """
        one_hot_a = np.zeros(self.num_actions)
        one_hot_a[action] = 1
        
        # Normalize reward before storing
        normalized_reward = self.normalize_reward(reward)
        
        self.replay_buffer.append((state, one_hot_a, normalized_reward, next_state, next_mean_action))

    def update(self):
        """
        Update agent networks with improved stability.
        
        Key improvements:
        1. Gradient clipping
        2. Target network hard updates
        3. Loss tracking for monitoring
        """
        if len(self.replay_buffer) < self.batch_size:
            return None
        
        # Sample batch
        batch_indices = np.random.choice(len(self.replay_buffer), self.batch_size, replace=False)
        batch_data = [self.replay_buffer[i] for i in batch_indices]
        
        states = np.array([item[0] for item in batch_data], dtype=np.float32)
        actions = np.array([item[1] for item in batch_data], dtype=np.float32)
        rewards = np.array([item[2] for item in batch_data], dtype=np.float32)
        next_states = np.array([item[3] for item in batch_data], dtype=np.float32)
        next_mean_actions = np.array([item[4] for item in batch_data], dtype=np.float32)
        
        # Convert to tensors
        rewards_tensor = torch.FloatTensor(rewards).to(self.device)
        
        # Compute current Q-values
        current_inputs = np.concatenate([states, actions, next_mean_actions], axis=1)
        current_inputs_tensor = torch.FloatTensor(current_inputs).to(self.device)
        current_q = self.qa_model(current_inputs_tensor).squeeze()
        
        # Compute next Q-values for action selection (Double DQN)
        with torch.no_grad():
            # Use online network to select actions
            next_q_values = []
            for a in range(self.num_actions):
                next_ak = np.eye(self.num_actions)[a]
                next_ak_batch = np.tile(next_ak, (self.batch_size, 1))
                next_inputs = np.concatenate([next_states, next_ak_batch, next_mean_actions], axis=1)
                next_inputs_tensor = torch.FloatTensor(next_inputs).to(self.device)
                next_q_values.append(self.qa_model(next_inputs_tensor))
            
            next_q_values = torch.cat(next_q_values, dim=1)
            best_actions = torch.argmax(next_q_values, dim=1)
            
            # Use target network to evaluate actions
            best_actions_one_hot = F.one_hot(best_actions, self.num_actions).float()
            next_inputs_target = np.concatenate([next_states, best_actions_one_hot.cpu().numpy(), next_mean_actions], axis=1)
            next_inputs_target_tensor = torch.FloatTensor(next_inputs_target).to(self.device)
            next_q_target = self.qb_model(next_inputs_target_tensor).squeeze()
            
            # Compute target Q-values
            targets = rewards_tensor + self.gamma * next_q_target
        
        # Compute loss (Huber loss for robustness)
        loss = F.smooth_l1_loss(current_q, targets)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        
        # Clip gradients
        torch.nn.utils.clip_grad_norm_(self.qa_model.parameters(), self.gradient_clip)
        
        self.optimizer.step()
        self.lr_scheduler.step()
        
        # Track loss
        self.loss_history.append(float(loss.item()))
        
        # Update target network
        self.training_steps += 1
        
        # Hard update every N steps for stability
        if self.training_steps % self.update_target_every == 0:
            self.qb_model.load_state_dict(self.qa_model.state_dict())
        # Also do soft updates for smoother transitions
        else:
            for target_param, param in zip(self.qb_model.parameters(), self.qa_model.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
        
        return float(loss.item())
    
    def get_stats(self):
        """Get agent statistics for monitoring."""
        return {
            'epsilon': self.epsilon,
            'buffer_size': len(self.replay_buffer),
            'training_steps': self.training_steps,
            'avg_loss': np.mean(self.loss_history) if self.loss_history else 0,
            'reward_mean': self.reward_mean,
            'reward_std': self.reward_std,
        }
    
    def save(self, filepath):
        """Save model checkpoint."""
        torch.save({
            'qa_model_state_dict': self.qa_model.state_dict(),
            'qb_model_state_dict': self.qb_model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'training_steps': self.training_steps,
            'epsilon': self.epsilon,
            'reward_mean': self.reward_mean,
            'reward_std': self.reward_std,
        }, filepath)
    
    def load(self, filepath):
        """Load model checkpoint."""
        try:
            checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)
        except TypeError:
            # Fallback for older torch versions
            checkpoint = torch.load(filepath, map_location=self.device)
        self.qa_model.load_state_dict(checkpoint['qa_model_state_dict'])
        self.qb_model.load_state_dict(checkpoint['qb_model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.training_steps = checkpoint['training_steps']
        self.epsilon = checkpoint['epsilon']
        self.reward_mean = checkpoint['reward_mean']
        self.reward_std = checkpoint['reward_std']

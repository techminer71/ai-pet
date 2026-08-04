#!/usr/bin/python3
# npc_net.py

import random
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, state_size, action_size):
        super(QNetwork, self).__init__()
        # Basic feed-forward architecture with 2 hidden layers
        self.fc1 = nn.Linear(state_size, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, action_size)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class NPCAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000) # Experience replay buffer
        
        # Hyperparameters
        self.gamma = 0.99          # Discount rate for future rewards
        self.epsilon = 1.0         # Exploration rate
        self.epsilon_min = 0.01    # Minimum exploration rate
        self.epsilon_decay = 0.995 # Decay factor per step
        self.learning_rate = 0.001
        self.batch_size = 32       # Batch size for training
        
        # Policy and Target Networks
        self.model = QNetwork(state_size, action_size)
        self.target_model = QNetwork(state_size, action_size)
        self.update_target_network()
        
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.criterion = nn.MSELoss()

    def update_target_network(self):
        self.target_model.load_state_dict(self.model.state_dict())

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        # Epsilon-greedy: Choose random action or predict best action
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        
        state = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            action_values = self.model(state)
        return torch.argmax(action_values).item()

    def replay(self):
        if len(self.memory) < self.batch_size:
            return

        # Sample a random mini-batch from memory
        minibatch = random.sample(self.memory, self.batch_size)
        
        states = torch.FloatTensor([m[0] for m in minibatch])
        actions = torch.LongTensor([m[1] for m in minibatch]).unsqueeze(1)
        rewards = torch.FloatTensor([m[2] for m in minibatch])
        next_states = torch.FloatTensor([m[3] for m in minibatch])
        dones = torch.FloatTensor([m[4] for m in minibatch])

        # Current predicted Q values
        current_q = self.model(states).gather(1, actions).squeeze(1)
        
        # Target Q values using Bellman Equation: Q(s,a) = r + gamma * max Q(s', a')
        with torch.no_grad():
            next_q = self.target_model(next_states).max(1)[0]
            target_q = rewards + (1 - dones) * self.gamma * next_q

        # Perform Backpropagation
        loss = self.criterion(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # Decay exploration rate
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


def main():
    # Configuration Example:
    # State dimensions (e.g., NPC X-pos, NPC Y-pos, Player X-pos, Player Y-pos)
    STATE_SIZE = 4 
    # Total unique actions (0: Move Left, 1: Move Right, 2: Attack)
    ACTION_SIZE = 3 
    
    agent = NPCAgent(STATE_SIZE, ACTION_SIZE)
    episodes = 500
    
    for e in range(episodes):
        # Reset game and get initial state vector
        # state = [npc.x, npc.y, player.x, player.y]
        state = np.array([0.0, 0.0, 5.0, 5.0]) 
        done = False
        
        while not done:
            # 1. Agent chooses action
            action = agent.act(state)
            
            # 2. Advance game engine step based on action
            # next_state, reward, done = game_engine.step(action)
            # Mock calculation example:
            next_state = state + np.array([0.1, 0.0, 0.0, 0.0]) if action == 1 else state
            reward = 1.0 if action == 1 else -0.1 
            done = True if state[0] >= 5.0 else False
            
            # 3. Store the transition data
            agent.remember(state, action, reward, next_state, done)
            
            # 4. Step forward the state
            state = next_state
            
            # 5. Train the network weights
            agent.replay()
            
        # Periodically align target network weights
        if e % 10 == 0:
            agent.update_target_network()

if __name__ == '__main__':
    main()

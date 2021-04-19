from numpy.random import RandomState
from typing import Any
from numpy import arange
from copy import deepcopy
from pydeeprecsys.rl.neural_networks.dueling import DuelingDDQN
from pydeeprecsys.rl.experience_replay.priority_replay_buffer import (
    PrioritizedExperienceReplayBuffer,
)
from pydeeprecsys.rl.agents.agent import ReinforcementLearning


class RainbowDQNAgent(ReinforcementLearning):

    """Instead of sampling randomly from the buffer we prioritize experiences with PER
    Instead of epsilon-greedy we use gaussian noisy layers for exploration
    Instead of the Q value we calculate Value and Advantage (Dueling DQN).
    This implementation does not include the Categorical DQN part."""

    def __init__(
        self,
        input_size: int,
        output_size: int,
        network_update_frequency: int = 5,
        network_sync_frequency: int = 200,
        priority_importance: float = 0.6,
        priority_weigth_growth: float = 0.001,
        buffer_size: int = 10000,
        buffer_burn_in: int = 1000,
        batch_size: int = 32,
        noise_sigma: float = 0.017,
        discount_factor: float = 0.99,
        learning_rate: float = 0.99,
        random_state: RandomState = RandomState(),
    ):

        self.network = DuelingDDQN(
            input_size, output_size, learning_rate, noise_sigma, discount_factor
        )
        self.target_network = deepcopy(self.network)

        self.buffer = PrioritizedExperienceReplayBuffer(
            max_experiences=buffer_size,
            min_experiences_to_start_predicting=buffer_burn_in,
            batch_size=batch_size,
            alpha=priority_importance,
            beta_growth=priority_weigth_growth,
            random_state=random_state,
        )
        self.step_count = 0
        self.network_update_frequency = network_update_frequency
        self.network_sync_frequency = network_sync_frequency
        self.actions = arange(output_size)
        self.random_state = random_state

    def _check_update_network(self):
        # we only start training the network once the buffer is ready
        # (the burn in is filled)
        if self.buffer.ready_to_predict():
            self.step_count += 1
            if self.step_count % self.network_update_frequency == 0:
                # we train at every K steps
                self.network.learn_with(self.buffer, self.target_network)
            if self.step_count % self.network_sync_frequency == 0:
                # at every N steps replaces the target network with the main network
                self.target_network.load_state_dict(self.network.state_dict())

    def action_for_state(self, state: Any) -> Any:
        state_flat = state.flatten()
        if self.buffer.ready_to_predict():
            action = self.target_network.best_action_for_state(state_flat)
        else:
            action = self.random_state.choice(self.actions)
        self._check_update_network()
        return action

    def store_experience(
        self, state: Any, action: Any, reward: float, done: bool, new_state: Any
    ):
        state_flat = state.flatten()
        new_state_flat = new_state.flatten()
        self.buffer.store_experience(state_flat, action, reward, done, new_state_flat)
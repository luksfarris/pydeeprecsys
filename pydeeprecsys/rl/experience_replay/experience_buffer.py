from abc import ABC, abstractmethod
from collections import namedtuple, deque
from numpy.random import RandomState
from typing import List, Tuple, Any

Experience = namedtuple(
    "Experience", field_names=["state", "action", "reward", "done", "next_state"]
)


class ExperienceBuffer(ABC):
    @abstractmethod
    def ready_to_predict(self) -> bool:
        pass

    @abstractmethod
    def sample_batch(self) -> List[Tuple]:
        pass

    @abstractmethod
    def store_experience(
        self, state: Any, action: Any, reward: float, done: bool, next_state: Any
    ):
        pass


class ExperienceReplayBuffer(ExperienceBuffer):
    def __init__(
        self,
        max_experiences: int = 50,
        minimum_experiences_to_start_predicting: int = 32,
        batch_size: int = 32,
        random_state: RandomState = RandomState(),
    ):
        self.minimum_experiences_to_start_predicting = (
            minimum_experiences_to_start_predicting
        )
        self.random_state = random_state
        # create double ended queue to store the experiences
        self.experience_queue = deque(maxlen=max_experiences)
        self.batch_size = batch_size

    def sample_batch(self) -> List[Tuple]:
        """ Samples a given number of experiences from the queue """
        # samples the index of `batch_size` different experiences from the replay memory
        samples = self.random_state.choice(
            len(self.experience_queue), self.batch_size, replace=False
        )
        # get the experiences
        experiences = [self.experience_queue[i] for i in samples]
        # returns a flattened list of the samples
        return zip(*experiences)

    def store_experience(
        self, state: Any, action: Any, reward: float, done: bool, next_state: Any
    ):
        """ Stores a new experience in the queue """
        experience = Experience(state, action, reward, done, next_state)
        # append to the right (end) of the queue
        self.experience_queue.append(experience)

    def ready_to_predict(self):
        """Returns true only if we had enough experiences to start predicting
        (measured by the burn in)"""
        return (
            len(self.experience_queue) >= self.minimum_experiences_to_start_predicting
        )
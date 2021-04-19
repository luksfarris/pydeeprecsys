from gym import make, spec, Env
from collections import namedtuple, defaultdict
from typing import Any, List
import math
from numpy import mean
import highway_env  # noqa: F401
import pydeeprecsys.movielens_fairness_env  # noqa: F401
import pydeeprecsys.interest_evolution_env  # noqa: F401
from pydeeprecsys.rl.agents.agent import ReinforcementLearning
from pydeeprecsys.rl.agents.dqn import DQNAgent
from pydeeprecsys.rl.learning_statistics import LearningStatistics


# An episode output is a data model to represent 3 things: how many timesteps the
# episode took to finish, the total sum of rewards, and the average reward sum of the
# last 100 episodes.
EpisodeOutput = namedtuple("EpisodeOutput", "timesteps,reward_sum")


class Manager(object):
    """ Class for learning from gym environments with some convenience methods. """

    env_name: str
    env: Any

    def __init__(
        self,
        env_name: str = None,
        random_state: int = 42,
        env: Env = None,
        max_episode_steps: int = math.inf,
        reward_threshold: float = math.inf,
    ):
        assert env_name is not None or env is not None
        if env_name is not None:
            self.env_name = env_name
            # extract some parameters from the environment
            self.max_episode_steps = (
                spec(self.env_name).max_episode_steps or max_episode_steps
            )
            self.reward_threshold = (
                spec(self.env_name).reward_threshold or reward_threshold
            )
            # create the environment
            self.env = make(env_name)
            # we seed the environment so that results are reproducible
            self.env.seed(random_state)
        else:
            self.env = env
            self.max_episode_steps = max_episode_steps
            self.reward_threshold = reward_threshold

    def print_overview(self):
        """ Prints the most important variables of the environment. """
        print("Reward threshold: {} ".format(self.reward_threshold))
        print("Reward signal range: {} ".format(self.env.reward_range))
        print("Maximum episode steps: {} ".format(self.max_episode_steps))
        print("Action apace size: {}".format(self.env.action_space))
        print("Observation space size {} ".format(self.env.observation_space))

    def execute_episodes(
        self,
        rl: ReinforcementLearning,
        n_episodes: int = 1,
        should_render: bool = False,
        should_print: bool = False,
    ) -> List[EpisodeOutput]:
        """Execute any number of episodes with the given agent.
        Returns the number of timesteps and sum of rewards per episode."""
        episode_outputs = []
        for episode in range(n_episodes):
            t, reward_sum, done, state = 0, 0, False, self.env.reset()
            if should_print:
                print(f"Running episode {episode}, starting at state {state}")
            while not done and t < self.max_episode_steps:
                if should_render:
                    self.env.render()
                action = rl.action_for_state(state)
                state, reward, done, _ = self.env.step(action)
                if should_print:
                    print(f"t={t} a={action} r={reward} s={state}")
                reward_sum += reward
                t += 1
            episode_outputs.append(EpisodeOutput(t, reward_sum))
            self.env.close()
        return episode_outputs

    def train(self, rl: DQNAgent, max_episodes=50, should_print: bool = True):
        if should_print is True:
            print("Training...")
        LearningStatistics.clear()
        episode_rewards = []
        for episode in range(max_episodes):
            state = self.env.reset()
            rewards = []
            done = False
            while done is False:
                action = rl.action_for_state(state)
                new_state, reward, done, _ = self.env.step(action)
                rl.store_experience(
                    state, action, reward, done, new_state
                )  # guardar experiencia en el buffer
                rewards.append(reward)
                state = new_state.copy()
            episode_rewards.append(sum(rewards))
            moving_average = mean(episode_rewards[-100:])
            LearningStatistics.episode_rewards.append(sum(rewards))
            LearningStatistics.timestep_rewards.append(rewards)
            LearningStatistics.moving_rewards.append(moving_average)
            if should_print is True:
                print(
                    "\rEpisode {:d} Mean Rewards {:.2f} \t\t".format(
                        episode, moving_average
                    ),
                    end="",
                )
            if moving_average >= self.reward_threshold:
                if should_print is True:
                    print("Reward threshold reached")
                break

    def hyperparameter_search(
        self,
        agent: type,
        params: dict,
        default_params: dict,
        episodes: int = 100,
        runs_per_combination: int = 3,
    ) -> dict:
        """Given an agent class, and a dictionary of hyperparameter names and values,
        will try all combinations, and return the mean reward of each combinatio
        for the given number of episods, and will run the determined number of times."""
        combination_results = defaultdict(lambda: [])
        for (p_name, p_value) in params.items():
            if len(p_value) < 2:
                continue
            for value in p_value:
                rl = agent(**{p_name: value, **default_params})
                combination_key = f"{p_name}={value}"
                for run in range(runs_per_combination):
                    print(f"Testing combination {p_name}={value} round {run}")
                    self.train(rl=rl, max_episodes=episodes, should_print=False)
                    combination_results[combination_key].append(
                        LearningStatistics.moving_rewards[-1]
                    )
                    print(f"result was {LearningStatistics.moving_rewards[-1]}")
        return combination_results


class HighwayManager(Manager):
    def __init__(self, random_state: int = 42, vehicles: int = 50):
        super().__init__(env_name="highway-v0", random_state=random_state)
        self.env.configure({"vehicles_count": vehicles})
        self.max_episode_steps = self.env.config["duration"]


class CartpoleManager(Manager):
    def __init__(self, random_state: int = 42):
        super().__init__(env_name="CartPole-v0", random_state=random_state)
        self.reward_threshold = 100


class MovieLensFairnessManager(Manager):
    def __init__(self, random_state: int = 42):
        super().__init__(env_name="MovieLensFairness-v0", random_state=random_state)


class InterestEvolutionManager(Manager):
    def __init__(self, random_state: int = 42):
        super().__init__(env_name="InterestEvolution-v0", random_state=random_state)
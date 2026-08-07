"""
RL agent for dynamic resource allocation.
"""

from __future__ import annotations

import os
import pickle
from typing import Any

import numpy as np

from scheduler.baseline import RuleBasedScheduler
from scheduler.env import SlicingEnv, SERVICE_CLASSES

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


class RLAgent:
    """RL scheduler with trained policy or rule-based fallback."""

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or os.path.join(MODEL_DIR, "rl_agent.pkl")
        self.baseline = RuleBasedScheduler()
        self.policy = None
        if os.path.exists(self.model_path):
            self.load()

    def decide(
        self,
        context_id: str,
        network_state: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        if self.policy is not None and network_state is not None:
            obs = self._state_to_observation(context_id, network_state)
            action = np.array(self.policy.predict(obs.reshape(1, -1))[0])
            return self._action_to_allocation(context_id, action)

        return self.baseline.decide(context_id)

    def train(self, episodes: int = 200) -> dict[str, Any]:
        env = SlicingEnv()
        training_rewards = []

        try:
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.multioutput import MultiOutputRegressor
        except ImportError:
            return self._train_baseline_comparison(episodes)

        states, actions, rewards = [], [], []

        for episode in range(episodes):
            obs = env.reset()
            episode_reward = 0
            done = False

            while not done:
                action = np.random.uniform(0.5, 2.0, size=4)
                next_obs, reward, done, info = env.step(action)
                states.append(obs)
                actions.append(action)
                rewards.append(reward)
                episode_reward += reward
                obs = next_obs

            training_rewards.append(episode_reward)

        X = np.array(states)
        y = np.array(actions)
        base = GradientBoostingRegressor(n_estimators=50, random_state=42)
        self.policy = MultiOutputRegressor(base)
        self.policy.fit(X, y)
        self.save()

        baseline_rewards = self._evaluate_baseline(episodes=20)

        return {
            "episodes": episodes,
            "mean_rl_reward": float(np.mean(training_rewards[-20:])),
            "mean_baseline_reward": float(np.mean(baseline_rewards)),
            "improvement": float(
                np.mean(training_rewards[-20:]) - np.mean(baseline_rewards)
            ),
        }

    def _train_baseline_comparison(self, episodes: int) -> dict[str, Any]:
        rewards = self._evaluate_baseline(episodes)
        return {
            "episodes": episodes,
            "mean_baseline_reward": float(np.mean(rewards)),
            "note": "sklearn not available; baseline only",
        }

    def _evaluate_baseline(self, episodes: int = 20) -> list[float]:
        env = SlicingEnv()
        rewards = []
        for _ in range(episodes):
            obs = env.reset()
            done = False
            ep_reward = 0
            while not done:
                context_id = env.contexts[env.current_context_idx % len(env.contexts)]
                allocation = self.baseline.decide(context_id)
                demands = self.baseline.demand_generator.get_demands(context_id)
                priorities = self.baseline.context_engine.get_context(context_id)
                qos = env._simulate_qos(allocation, demands)
                action = np.ones(4)
                obs, reward, done, _ = env.step(action)
                ep_reward += reward
            rewards.append(ep_reward)
        return rewards

    def _state_to_observation(
        self, context_id: str, state: dict[str, Any]
    ) -> np.ndarray:
        env = SlicingEnv()
        ctx_idx = env.contexts.index(context_id) if context_id in env.contexts else 0
        env.current_context_idx = ctx_idx
        return env._get_observation(
            state.get("allocation"),
            state.get("demands"),
            state.get("measured_qos"),
        )

    def _action_to_allocation(
        self, context_id: str, action: np.ndarray
    ) -> dict[str, float]:
        priorities = self.baseline.context_engine.get_context(context_id)
        demands = self.baseline.demand_generator.get_demands(context_id)
        adjusted = {}
        action = np.clip(action, 0.1, 10.0)
        for i, service in enumerate(SERVICE_CLASSES):
            adjusted[service] = priorities.get(service, 1) * action[i]
        return self.baseline.allocation_engine.allocate(
            self.baseline.total_bandwidth, adjusted, demands
        )

    def save(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(self.model_path, "wb") as handle:
            pickle.dump({"policy": self.policy}, handle)

    def load(self):
        with open(self.model_path, "rb") as handle:
            data = pickle.load(handle)
        self.policy = data.get("policy")

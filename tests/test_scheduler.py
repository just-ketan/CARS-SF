"""Tests for RL scheduler and baseline."""

import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.baseline import RuleBasedScheduler
from scheduler.env import SlicingEnv


def test_baseline_scheduler():
    scheduler = RuleBasedScheduler()
    allocation = scheduler.decide("disaster")
    assert sum(allocation.values()) <= 100.01
    assert allocation["healthcare"] > 0


def test_env_reset_and_step():
    env = SlicingEnv()
    obs = env.reset()
    assert obs.shape == (16,)
    action = np.ones(4)
    next_obs, reward, done, info = env.step(action)
    assert next_obs.shape == (16,)
    assert isinstance(reward, float)
    assert "allocation" in info


def test_env_all_contexts():
    env = SlicingEnv()
    for _ in range(4):
        obs = env.reset()
        action = np.array([1.0, 1.5, 0.8, 0.5])
        _, reward, done, info = env.step(action)
        assert reward != 0 or done


def test_reward_measures_satisfaction_against_demand():
    scheduler = RuleBasedScheduler()
    priorities = {"healthcare": 1, "education": 1, "agriculture": 1, "general": 1}
    allocation = {s: 10.0 for s in priorities}
    measured = {s: {"throughput_mbps": 10.0, "latency_ms": 10} for s in priorities}
    full = scheduler.compute_reward(allocation, measured, priorities, {s: 10.0 for s in priorities})
    half = scheduler.compute_reward(allocation, measured, priorities, {s: 20.0 for s in priorities})
    assert full == 100.0
    assert half == 50.0


def test_cem_agent_trains_on_sequential_env_and_reloads(tmp_path):
    from scheduler.agent import RLAgent

    agent = RLAgent(model_path=str(tmp_path / "rl.pkl"))
    results = agent.train(episodes=3, population=6, eval_episodes=1, episode_steps=6)
    assert "SequentialSlicingEnv" in results["algorithm"]
    for context, scores in results["per_context"].items():
        # Selection is on validation seeds: the chosen policy never loses there.
        assert scores["validation_rl_reward"] >= scores["validation_baseline_reward"], context
        assert all(0.1 <= m <= 10 for m in scores["multipliers"].values())
    reloaded = RLAgent(model_path=str(tmp_path / "rl.pkl"))
    assert reloaded.is_trained
    assert sum(reloaded.decide("disaster").values()) <= 100.01


if __name__ == "__main__":
    test_baseline_scheduler()
    test_env_reset_and_step()
    test_env_all_contexts()
    print("All scheduler tests passed.")

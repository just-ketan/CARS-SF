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


if __name__ == "__main__":
    test_baseline_scheduler()
    test_env_reset_and_step()
    test_env_all_contexts()
    print("All scheduler tests passed.")

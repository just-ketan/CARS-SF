"""Sequential environment dynamics and policy plumbing."""

import numpy as np

from scheduler.env_seq import SequentialSlicingEnv, evaluate_policy


def test_env_spaces_and_step():
    env = SequentialSlicingEnv(seed=0)
    obs, _ = env.reset(seed=0)
    assert env.observation_space.contains(obs)
    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
    assert env.observation_space.contains(obs)
    assert isinstance(reward, float) and not terminated
    assert set(info["satisfaction"]) == {"healthcare", "education", "agriculture", "general"}


def test_underprovisioning_builds_backlog_that_carries_over():
    env = SequentialSlicingEnv(seed=0)
    env.reset(seed=0, options={"context": "school"})
    starve_general = np.array([0.0, 0.0, 0.0, -1.0])
    _, _, _, _, info = env.step(starve_general)
    assert info["satisfaction"]["general"] < 1.0
    assert env.backlog[3] > 0


def test_satisfied_slices_see_only_propagation_delay():
    env = SequentialSlicingEnv(seed=0)
    env.reset(seed=0, options={"context": "normal"})
    _, _, _, _, info = env.step(np.zeros(4))
    assert info["delay_ms"]["healthcare"] == env.calibration["prop_delay_ms"]["healthcare"]


def test_evaluate_policy_is_deterministic_for_seed():
    a = evaluate_policy(lambda obs, env: np.zeros(4), episodes=2, seed=7)
    b = evaluate_policy(lambda obs, env: np.zeros(4), episodes=2, seed=7)
    assert a == b

"""
Gymnasium-compatible environment for RL-based resource allocation.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from scheduler.baseline import RuleBasedScheduler

SERVICE_CLASSES = ["healthcare", "education", "agriculture", "general"]


class SlicingEnv:
    """
    RL environment wrapping network state for resource allocation.

    Observation: [context_one_hot(len(contexts)), demands(4), allocations(4), qos_metrics(4)]
    Action: priority weight adjustments (4 continuous values)

    Context transitions do not depend on the action, so this is a contextual
    bandit: the optimal policy is the best action per context.
    """

    def __init__(
        self,
        total_bandwidth: float = 100.0,
        contexts: list[str] | None = None,
    ):
        self.total_bandwidth = total_bandwidth
        self.contexts = contexts or ["normal", "school", "harvest", "disaster"]
        self.baseline = RuleBasedScheduler(total_bandwidth)
        self.current_context_idx = 0
        self.step_count = 0
        self.max_steps = 100

        self.observation_dim = len(self.contexts) + 4 + 4 + 4
        self.action_dim = 4

    @property
    def observation_space_shape(self) -> tuple[int, ...]:
        return (self.observation_dim,)

    @property
    def action_space_shape(self) -> tuple[int, ...]:
        return (self.action_dim,)

    def reset(self) -> np.ndarray:
        self.current_context_idx = 0
        self.step_count = 0
        return self._get_observation()

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        context_id = self.contexts[self.current_context_idx % len(self.contexts)]
        demands = self.baseline.demand_generator.get_demands(context_id)

        base_priorities = self.baseline.context_engine.get_context(context_id)
        adjusted = {}
        action = np.clip(action, 0.1, 10.0)
        for i, service in enumerate(SERVICE_CLASSES):
            adjusted[service] = base_priorities[service] * action[i]

        allocation = self.baseline.allocation_engine.allocate(
            self.total_bandwidth, adjusted, demands
        )

        measured_qos = self._simulate_qos(allocation, demands)
        reward = self.baseline.compute_reward(
            allocation, measured_qos, base_priorities, demands
        )

        self.step_count += 1
        self.current_context_idx += 1
        done = self.step_count >= self.max_steps

        info = {
            "context": context_id,
            "allocation": allocation,
            "demands": demands,
            "measured_qos": measured_qos,
        }

        return self._get_observation(allocation, demands, measured_qos), reward, done, info

    def _get_observation(
        self,
        allocation: dict[str, float] | None = None,
        demands: dict[str, float] | None = None,
        qos: dict[str, dict] | None = None,
    ) -> np.ndarray:
        context_one_hot = np.zeros(len(self.contexts))
        context_one_hot[self.current_context_idx % len(self.contexts)] = 1.0

        demand_vec = np.array([
            (demands or {}).get(s, 20.0) for s in SERVICE_CLASSES
        ]) / 100.0

        alloc_vec = np.array([
            (allocation or {}).get(s, 25.0) for s in SERVICE_CLASSES
        ]) / 100.0

        qos_vec = np.array([
            (qos or {}).get(s, {}).get("throughput_mbps", 0) for s in SERVICE_CLASSES
        ]) / 100.0

        return np.concatenate([context_one_hot, demand_vec, alloc_vec, qos_vec])

    def evaluate(self, context_id: str, action: np.ndarray) -> float:
        """Reward of a single action in a given context (no state change)."""
        demands = self.baseline.demand_generator.get_demands(context_id)
        base_priorities = self.baseline.context_engine.get_context(context_id)
        action = np.clip(action, 0.1, 10.0)
        adjusted = {s: float(base_priorities[s] * action[i]) for i, s in enumerate(SERVICE_CLASSES)}
        allocation = self.baseline.allocation_engine.allocate(
            self.total_bandwidth, adjusted, demands
        )
        qos = self._simulate_qos(allocation, demands)
        return self.baseline.compute_reward(allocation, qos, base_priorities, demands)

    def _simulate_qos(
        self, allocation: dict[str, float], demands: dict[str, float]
    ) -> dict[str, dict[str, float]]:
        qos = {}
        for service in SERVICE_CLASSES:
            allocated = allocation.get(service, 0)
            demand = demands.get(service, 1)
            throughput = min(allocated, demand) * 0.95
            latency = 10 + max(0, demand - allocated) * 2
            qos[service] = {
                "throughput_mbps": throughput,
                "latency_ms": latency,
            }
        return qos

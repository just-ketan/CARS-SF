"""
RL transitions of the live (Mininet) control loop.

    Observe → State → Decide → Enforce → Measure → Reward → (next) State

Every controller decision opens a transition: the observation (same layout as
``SequentialSlicingEnv``), the policy's action (log10 priority multipliers, the
simulator's action space) and the enforcement record of the resulting
allocation. Per-tick rewards (``scheduler/reward.py``, the same function the
simulator uses) are accumulated until the next decision, which closes the
transition with the mean reward over the interval and the next observation.

Transitions whose allocation failed to apply (``enforcement.verified is
False``) are kept for the record but never handed to a learner: the network
did not take that action, so its reward says nothing about it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

SERVICES = ("healthcare", "education", "agriculture", "general")


def action_from_multipliers(multipliers: dict[str, float]) -> list[float]:
    return [round(float(np.log10(np.clip(multipliers.get(s, 1.0), 0.1, 10.0))), 4) for s in SERVICES]


class TransitionLog:
    def __init__(self, learner: Callable[[str, list[float], float], None] | None = None):
        self.learner = learner
        self.records: list[dict[str, Any]] = []
        self._pending: dict[str, Any] | None = None
        self._rewards: list[float] = []
        self._enforcement_of: Callable[[int], dict | None] = lambda index: None

    def bind_enforcement(self, lookup: Callable[[int], dict | None]):
        """``lookup(history_index)`` returns the enforcement record of a decision."""
        self._enforcement_of = lookup

    def decision(self, tick: int, obs: np.ndarray, action: list[float], context: str,
                 allocation: dict[str, float], history_index: int, applied: bool):
        self._close(tick, obs, done=False)
        self._pending = {
            "tick": tick, "context": context, "obs": [round(float(v), 5) for v in obs],
            "action": action, "allocation": dict(allocation), "history_index": history_index,
            "allocation_changed": applied,
        }
        self._rewards = []

    def reward(self, reward: float):
        if self._pending is not None:
            self._rewards.append(float(reward))

    def finish(self, tick: int, obs: np.ndarray):
        if self._pending is not None and not self._rewards and self.records:
            # A decision on the last tick has no measured interval: no transition,
            # and the episode ends on the previous one.
            self.records[-1]["done"] = True
        self._close(tick, obs, done=True)
        self._pending = None

    def _close(self, tick: int, next_obs: np.ndarray, done: bool):
        if self._pending is None or not self._rewards:
            return
        pending = self._pending
        enforcement = self._enforcement_of(pending["history_index"])
        # An unchanged allocation keeps the previous (verified) one in force.
        verified = True if not pending["allocation_changed"] else (enforcement or {}).get("verified")
        record = {
            **{k: v for k, v in pending.items() if k != "history_index"},
            "reward": round(float(np.mean(self._rewards)), 4),
            "reward_ticks": len(self._rewards),
            "next_tick": tick,
            "next_obs": [round(float(v), 5) for v in next_obs],
            "done": done,
            "enforcement_verified": verified,
            "learnable": verified is not False,
        }
        self.records.append(record)
        if self.learner is not None and record["learnable"]:
            self.learner(record["context"], record["action"], record["reward"])

    def write(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record) + "\n")

    def summary(self) -> dict[str, Any]:
        rewards = [r["reward"] for r in self.records]
        return {
            "transitions": len(self.records),
            "learnable": sum(r["learnable"] for r in self.records),
            "unverified": sum(r["enforcement_verified"] is None for r in self.records),
            "failed_enforcement": sum(r["enforcement_verified"] is False for r in self.records),
            "mean_reward": round(float(np.mean(rewards)), 4) if rewards else None,
        }

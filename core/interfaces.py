"""Contracts between pipeline stages (architecture.md Principle 4).

Every stage is replaceable by any object satisfying its protocol; the
composition is data-driven (``registries/schedulers.yaml``) so a new allocator,
priority policy or QoS backend plugs in without touching the other modules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

Allocation = dict[str, float]


@runtime_checkable
class ContextSource(Protocol):
    def step(self, tick: int) -> dict[str, Any]: ...


@runtime_checkable
class DemandEstimator(Protocol):
    def observe(self, snapshot: dict[str, Any], allocation: Allocation) -> dict[str, float]: ...
    def estimate(self) -> dict[str, float]: ...


@runtime_checkable
class PriorityPolicy(Protocol):
    def __call__(self, context_id: str, state: dict[str, Any]) -> dict[str, float]: ...


@runtime_checkable
class Allocator(Protocol):
    name: str
    def allocate(self, capacity: float, priorities: dict, demands: dict) -> Allocation: ...


@runtime_checkable
class QoSBackend(Protocol):
    def setup_htb(self, total_bandwidth_mbps: float = 100.0, spawns: list | None = None): ...
    def apply_allocation(self, allocation: Allocation): ...


@runtime_checkable
class Healer(Protocol):
    def handle(self, events: list[dict[str, Any]], tick: int): ...
    def constraints(self) -> dict[str, Any]: ...


class TelemetrySource(ABC):
    """Collects measurable network statistics."""

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def poll(self, tick: int) -> dict[str, Any]:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def get_snapshots(self) -> list[dict[str, Any]]:
        pass


class FeatureExtractor(ABC):
    """Transforms raw telemetry into ML feature vectors."""

    @abstractmethod
    def extract(self) -> list[dict[str, Any]]:
        pass


class DatasetExporter(ABC):
    """Exports aligned records to disk."""

    @abstractmethod
    def export(self, records: list[dict[str, Any]], output_path: str) -> str:
        pass

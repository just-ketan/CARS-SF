"""Abstract interfaces for pipeline stages."""

from abc import ABC, abstractmethod
from typing import Any


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


class Labeler(ABC):
    """Assigns deterministic ground-truth labels."""

    @abstractmethod
    def label(
        self,
        features: list[dict[str, Any]],
        spawn_metadata: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        pass


class DatasetExporter(ABC):
    """Exports aligned records to disk."""

    @abstractmethod
    def export(self, records: list[dict[str, Any]], output_path: str) -> str:
        pass

"""Unified YAML configuration loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRIES_DIR = REPO_ROOT / "registries"
RESULTS_DIR = REPO_ROOT / "results"
GENERATED_DIR = REPO_ROOT / "generated"


def load_yaml(name: str, subdir: str = "registries") -> dict[str, Any]:
    path = REPO_ROOT / subdir / name
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_applications() -> list[dict[str, Any]]:
    data = load_yaml("applications.yaml")
    return data.get("applications", [])


def load_scenarios() -> list[dict[str, Any]]:
    data = load_yaml("scenarios.yaml")
    return data.get("scenarios", [])


def load_features() -> dict[str, Any]:
    return load_yaml("features.yaml")


def get_application_by_id(app_id: str) -> dict[str, Any] | None:
    for app in load_applications():
        if app["application_id"] == app_id:
            return app
    return None


def ensure_output_dirs() -> None:
    for directory in (
        RESULTS_DIR,
        GENERATED_DIR / "pcap",
        GENERATED_DIR / "telemetry",
        GENERATED_DIR / "datasets",
        GENERATED_DIR / "logs",
    ):
        os.makedirs(directory, exist_ok=True)

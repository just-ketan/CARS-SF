"""Provenance helpers: a content fingerprint of the code and registries.

Used in dataset manifests, per-run metadata and stale-artifact detection. It is
computed from file contents (not git), so it is valid for uncommitted work and
changes whenever any source file or registry changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from functools import lru_cache
from pathlib import Path

from core.config import REPO_ROOT

FINGERPRINT_DIRS = (
    "analysis", "classification", "context", "core", "dataset", "features", "monitoring",
    "registries", "scenario", "scheduler", "self_healing", "slicing", "telemetry", "topology",
    "traffic", "traffic_models", "validation",
)


@lru_cache(maxsize=1)
def code_fingerprint() -> str:
    digest = hashlib.sha256()
    for directory in FINGERPRINT_DIRS:
        root = REPO_ROOT / directory
        for path in sorted(root.rglob("*")):
            if path.suffix in (".py", ".yaml") and "__pycache__" not in path.parts:
                digest.update(str(path.relative_to(REPO_ROOT)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


MODEL_ARTIFACTS = (
    "scheduler/models/rl_agent.pkl", "scheduler/models/ppo_slicing.zip", "scheduler/models/calibration.json",
    "classification/models/slicenet_mininet.pkl", "classification/models/slicenet_cnn.pt",
    "classification/models/slicenet_baseline.pkl",
)


def model_fingerprint() -> str:
    """Hash of the trained artefacts a run loads (the online-CEM checkpoint is
    excluded: it is state that evolves by design, recorded per run instead)."""
    digest = hashlib.sha256()
    for rel in MODEL_ARTIFACTS:
        path = REPO_ROOT / rel
        digest.update(rel.encode())
        digest.update(file_sha256(path).encode() if path.exists() else b"missing")
    return digest.hexdigest()[:16]


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def environment_info() -> dict:
    versions = {}
    for module in ("numpy", "pandas", "sklearn", "torch", "stable_baselines3", "mininet", "dpkt"):
        try:
            versions[module] = getattr(__import__(module), "__version__", "unknown")
        except Exception:
            versions[module] = None
    return {"python": sys.version.split()[0], "platform": platform.platform(), "packages": versions}


def write_manifest(path: str | Path, payload: dict) -> str:
    record = {
        "created_unix": time.time(),
        "code_fingerprint": code_fingerprint(),
        "model_fingerprint": model_fingerprint(),
        "environment": environment_info(),
        **payload,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, default=str))
    return str(path)


def is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0

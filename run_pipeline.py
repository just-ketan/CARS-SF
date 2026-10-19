#!/usr/bin/env python3
"""
CARS-SF end-to-end pipeline: one entry point, explicit modes, fail-fast.

    .venv/bin/python run_pipeline.py --mode unit        # unit + contract tests
    .venv/bin/python run_pipeline.py --mode synthetic   # RSNSD → SliceNet baseline → RL (simulator) → evaluation
    .venv/bin/python run_pipeline.py --mode mininet     # emulated-network integration tests (incl. coupled RL loop)
    .venv/bin/python run_pipeline.py --mode rl          # RL training + coupled live-loop test
    .venv/bin/python run_pipeline.py --mode full        # everything, incl. Mininet collection and the thesis matrix

Stages run as subprocesses of real repository commands; each one's command,
exit code, duration and log are recorded in results/pipeline/<id>/manifest.json
together with the code/model fingerprints, seeds and dataset provenance. The
first failing stage stops the pipeline (no silent skipping). Mininet stages run
sudo-free in user namespaces (tests/integration/harness.py) or on real Open
vSwitch when started as root.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
PY = sys.executable

MODES = ("unit", "synthetic", "mininet", "rl", "full")


def stages(mode: str, seed: int, matrix_workers: int) -> list[tuple[str, list[str]]]:
    unit = [("unit_tests", [PY, "-m", "pytest", "-q", "tests"])]
    synthetic = [
        ("rsnsd_generate_validate", [PY, "-m", "dataset.rsnsd", "--per-scenario", "6000", "--seed", str(seed)]),
        ("slicenet_synthetic_baseline", [PY, "experiments/run_slicenet_pipeline.py", "--baseline-only"]),
    ]
    rl_train = [("rl_train_cem_ppo", [PY, "scheduler/train.py", "--algo", "all", "--seeds", "0", "1", "2"])]
    rl_eval = [("rl_simulator_evaluation", [PY, "scheduler/train.py", "--evaluate-only"])]
    coupled = [("coupled_rl_loop_live", [PY, "-m", "pytest", "-q", "-m", "integration",
                                         "tests/integration/test_pipeline.py", "-k", "coupled"])]
    integration = [("mininet_integration", [PY, "-m", "pytest", "-q", "-m", "integration", "tests/integration"])]
    collect = [
        ("mininet_collect", [PY, "experiments/collect_dataset.py", "--seeds", "0", "1", "2"]),
        ("slicenet_mininet_and_transfer", [PY, "experiments/run_slicenet_pipeline.py"]),
    ]
    matrix = [
        ("matrix", [PY, "experiments/run_matrix.py", "--rerun-stale", "--workers", str(matrix_workers),
                    "--study", "main", "ablation", "sensitivity_capacity", "sensitivity_load",
                    "scalability", "resilience", "timeline", "slicenet_inloop"]),
        ("matrix_online_rl", [PY, "experiments/run_matrix.py", "--rerun-stale", "--workers", "1",
                              "--study", "online_rl"]),
        ("aggregate", [PY, "experiments/aggregate.py"]),
        ("plots", [PY, "experiments/plots/plot_thesis.py"]),
        ("report", [PY, "experiments/report.py"]),
    ]
    return {
        "unit": unit,
        "synthetic": unit + synthetic + rl_train + rl_eval,
        "mininet": unit + integration,
        "rl": unit + rl_train + rl_eval + coupled,
        "full": unit + synthetic + collect + rl_train + rl_eval + integration + matrix,
    }[mode]


def check_environment(mode: str) -> list[str]:
    """Fail-fast prerequisites for the requested mode; returns the problems found."""
    problems = []
    modules = ["numpy", "pandas", "sklearn", "scipy", "yaml", "dpkt", "pytest", "gymnasium"]
    if mode in ("synthetic", "rl", "full"):
        modules += ["torch", "stable_baselines3"]
    if mode in ("mininet", "rl", "full"):
        modules += ["mininet"]
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as exc:
            problems.append(f"python module {module!r} unavailable in {PY}: {exc}")
    if mode in ("mininet", "rl", "full"):
        for tool in ("tc", "ip", "tcpdump", "mnexec"):
            if shutil.which(tool) is None and not Path(f"/usr/sbin/{tool}").exists():
                problems.append(f"command {tool!r} not found")
        if os.geteuid() != 0:
            from tests.integration.harness import userns_available
            if not userns_available():
                problems.append("not root and unprivileged user namespaces are unavailable "
                                "(run as root or enable kernel.unprivileged_userns_clone)")
    return problems


def run(mode: str, seed: int, matrix_workers: int, dry_run: bool) -> int:
    from core.provenance import code_fingerprint, environment_info, model_fingerprint, write_manifest

    pipeline_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{mode}"
    out = REPO_ROOT / "results" / "pipeline" / pipeline_id
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "pipeline_id": pipeline_id, "mode": mode, "seed": seed, "root": os.geteuid() == 0,
        "code_fingerprint_at_start": code_fingerprint(), "model_fingerprint_at_start": model_fingerprint(),
        "stages": [], "status": "running",
    }
    problems = check_environment(mode)
    manifest["environment_check"] = {"ok": not problems, "problems": problems}
    if problems:
        manifest["status"] = "failed: environment"
        write_manifest(out / "manifest.json", manifest)
        print("Environment check failed:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 2

    for name, command in stages(mode, seed, matrix_workers):
        log_path = out / f"{len(manifest['stages']):02d}_{name}.log"
        print(f"[{name}] {' '.join(command)}", flush=True)
        record = {"stage": name, "command": " ".join(command), "log": str(log_path.relative_to(REPO_ROOT))}
        if dry_run:
            manifest["stages"].append({**record, "status": "dry-run"})
            continue
        started = time.time()
        with open(log_path, "w", encoding="utf-8") as log:
            proc = subprocess.run(command, cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        record.update({"exit_code": proc.returncode, "duration_s": round(time.time() - started, 1),
                       "status": "ok" if proc.returncode == 0 else "failed"})
        manifest["stages"].append(record)
        write_manifest(out / "manifest.json", manifest)
        tail = log_path.read_text(errors="replace").strip().splitlines()[-3:]
        print(f"[{name}] {record['status']} in {record['duration_s']} s  " + " | ".join(tail), flush=True)
        if proc.returncode != 0:
            manifest["status"] = f"failed at {name}"
            write_manifest(out / "manifest.json", manifest)
            print(f"Pipeline stopped: stage {name} failed (log: {log_path})", file=sys.stderr)
            return 1

    manifest["status"] = "ok" if not dry_run else "dry-run"
    manifest["artifacts"] = _artifacts()
    manifest["environment"] = environment_info()
    write_manifest(out / "manifest.json", manifest)
    print(f"Pipeline {mode}: {manifest['status']} → {out / 'manifest.json'}")
    return 0


def _artifacts() -> dict:
    """Provenance of the datasets and models the run produced or used."""
    from core.provenance import file_sha256

    def manifest_of(path: Path):
        return json.loads(path.read_text()) if path.exists() else None

    artifacts = {
        "rsnsd": manifest_of(REPO_ROOT / "RSNSD" / "dataset" / "raw" / "rsnsd_v1.0.manifest.json"),
        "mininet_dataset": manifest_of(REPO_ROOT / "generated" / "datasets" / "mininet_full_dataset.manifest.json"),
        "models": {},
    }
    for rel in ("scheduler/models/rl_agent.pkl", "scheduler/models/ppo_slicing.zip",
                "classification/models/slicenet_baseline.pkl", "classification/models/slicenet_mininet.pkl",
                "classification/models/slicenet_cnn.pt"):
        path = REPO_ROOT / rel
        artifacts["models"][rel] = file_sha256(path) if path.exists() else None
    for key in ("rsnsd", "mininet_dataset"):
        if artifacts[key]:
            artifacts[key] = {k: artifacts[key].get(k) for k in
                              ("schema_version", "provenance_source", "seed", "seeds", "rows", "sha256", "code_fingerprint")}
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--mode", choices=MODES, default="synthetic")
    parser.add_argument("--seed", type=int, default=42, help="RSNSD generation seed")
    parser.add_argument("--matrix-workers", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true", help="check the environment and list stages only")
    args = parser.parse_args()
    sys.exit(run(args.mode, args.seed, args.matrix_workers, args.dry_run))


if __name__ == "__main__":
    main()

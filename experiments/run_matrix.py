#!/usr/bin/env python3
"""
Run an experiment matrix (configs/experiments/*.yaml), resumably and in parallel.

    python experiments/run_matrix.py --config configs/experiments/thesis.yaml --study main --workers 3
    python experiments/run_matrix.py --config ... --list

Runs execute on the real network when launched as root, otherwise through the
sudo-free namespace harness. A run whose results/runs/<run_id>/summary.json
exists is skipped, so an interrupted matrix resumes where it stopped. Each
run records the config, seed, git commit and the code/model fingerprints
(core/provenance.py). A finished run whose fingerprints differ from the current
code and models is *stale*: it is reported, never silently reused, and is
re-run (old directory archived under results/runs_archive/) with --rerun-stale.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from core.config import RESULTS_DIR  # noqa: E402
from core.provenance import code_fingerprint, model_fingerprint  # noqa: E402

RUNS_DIR = RESULTS_DIR / "runs"
ARCHIVE_DIR = RESULTS_DIR / "runs_archive"
MATRIX_LOG = RESULTS_DIR / "matrix_log.jsonl"


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def expand(config: dict, study_name: str) -> list[dict]:
    study = config["studies"][study_name]
    base = {**config.get("defaults", {}), **study.get("base", {})}
    grid = study["grid"]
    keys = list(grid)
    runs = []
    for values in itertools.product(*(grid[k] for k in keys)):
        params = dict(base)
        label_parts = [study_name]
        for key, value in zip(keys, values):
            if key == "variant":
                variant = dict(value)
                params["variant"] = variant.pop("name")
                label_parts.append(params["variant"])
                params.update(variant)
            else:
                params[key] = value
        params.setdefault("scheduler", "proposed")
        params.setdefault("scenario", params.get("timeline") or "normal")
        for key in ("scenario", "scheduler"):
            if key not in keys:
                continue
            label_parts.append(str(params[key]))
        for key in keys:
            if key not in ("scenario", "scheduler", "seed", "variant"):
                label_parts.append(f"{key.replace('topo_', '')}{params[key]}")
        label_parts.append(f"s{params.get('seed', 0)}")
        params["run_id"] = "__".join(label_parts)
        params["study"] = study_name
        runs.append(params)
    return runs


def fingerprints() -> dict:
    return {"code_fingerprint": code_fingerprint(), "model_fingerprint": model_fingerprint()}


def run_state(run_id: str) -> str:
    """missing | current | stale"""
    run_dir = RUNS_DIR / run_id
    if not (run_dir / "summary.json").exists():
        return "missing"
    meta_path = run_dir / "run_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    current = fingerprints()
    return "current" if all(meta.get(k) == v for k, v in current.items()) else "stale"


def execute(params: dict, rerun_stale: bool = False) -> dict:
    run_dir = RUNS_DIR / params["run_id"]
    state = run_state(params["run_id"])
    if state == "current":
        return {"run_id": params["run_id"], "status": "skipped"}
    if state == "stale":
        if not rerun_stale:
            return {"run_id": params["run_id"], "status": "stale"}
        meta_path = run_dir / "run_meta.json"
        old = json.loads(meta_path.read_text()).get("code_fingerprint", "unknown") if meta_path.exists() else "unknown"
        target = ARCHIVE_DIR / old / params["run_id"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            import shutil
            shutil.rmtree(target)
        run_dir.rename(target)
    options = {k: v for k, v in params.items() if k not in ("scenario", "duration", "study", "variant")}
    started = time.time()
    try:
        if os.geteuid() == 0:
            from core.orchestrator import run_experiment
            topo_opts = {k: options.pop(k) for k in list(options) if k.startswith("topo_")}
            if topo_opts:
                from topology.rural_topology import RuralNetworkTopology
                options["topology_factory"] = lambda: RuralNetworkTopology(
                    ues_per_service=options.get("ues_per_service", 2),
                    mixed_ue=options.get("mixed_ue", False),
                    **{k[5:]: v for k, v in topo_opts.items()},
                )
            result = run_experiment(params["scenario"], params["duration"], **options)
        else:
            from tests.integration.harness import run_in_namespace
            result = run_in_namespace(params["scenario"], params["duration"],
                                      timeout=params["duration"] * 8 + 600, **options)
        status = "ok" if result.get("data_source") == "pcap" else "degraded"
    except Exception as exc:  # keep the matrix going; the log records the failure
        return {"run_id": params["run_id"], "status": "failed", "error": str(exc)[-2000:]}
    meta = {"params": params, "git_commit": git_commit(), **fingerprints(),
            "wall_time_s": round(time.time() - started, 1)}
    with open(run_dir / "run_meta.json", "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)
    return {"run_id": params["run_id"], "status": status, "wall_time_s": meta["wall_time_s"]}


def pd_counts(values) -> dict:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description="Run a CARS-SF experiment matrix")
    parser.add_argument("--config", default=os.path.join(REPO_ROOT, "configs", "experiments", "thesis.yaml"))
    parser.add_argument("--study", nargs="*", help="studies to run (default: all)")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--rerun-stale", action="store_true",
                        help="archive and re-run finished runs made with different code or models")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    studies = args.study or list(config["studies"])
    runs = [run for name in studies for run in expand(config, name)]
    if args.list:
        states = {run["run_id"]: run_state(run["run_id"]) for run in runs}
        for run in runs:
            print(f"{states[run['run_id']]:8s} {run['run_id']}")
        print(f"{len(runs)} runs: " + ", ".join(
            f"{v} {k}" for k, v in sorted(pd_counts(states.values()).items())))
        return

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{len(runs)} runs across {studies} with {args.workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool, open(MATRIX_LOG, "a", encoding="utf-8") as log:
        futures = {pool.submit(execute, run, args.rerun_stale): run for run in runs}
        for done, future in enumerate(as_completed(futures), 1):
            outcome = future.result()
            log.write(json.dumps({**outcome, "time": time.time()}) + "\n")
            log.flush()
            print(f"[{done}/{len(runs)}] {outcome['status']:8s} {outcome['run_id']} "
                  f"{outcome.get('wall_time_s', '')}{outcome.get('error', '')[:300]}", flush=True)


if __name__ == "__main__":
    main()

"""
RL agent for dynamic resource allocation.

The slicing environment is a contextual bandit (context transitions do not
depend on the action), so the agent learns one priority-adjustment vector per
context with the cross-entropy method (CEM), a gradient-free policy search.
The rule-based scheduler is the fallback for unknown contexts or when no
trained policy exists.
"""

from __future__ import annotations

import os
import pickle
from typing import Any

import numpy as np

from scheduler.baseline import RuleBasedScheduler
from scheduler.env import SERVICE_CLASSES

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def _all_contexts() -> list[str]:
    try:
        from core.config import load_scenarios
        return [s["id"] for s in load_scenarios()]
    except Exception:
        return ["normal", "school", "harvest", "disaster"]


class RLAgent:
    """RL scheduler with trained per-context policy or rule-based fallback."""

    def __init__(self, model_path: str | None = None, total_bandwidth: float = 100.0):
        self.model_path = model_path or os.path.join(MODEL_DIR, "rl_agent.pkl")
        self.baseline = RuleBasedScheduler(total_bandwidth)
        self.policy: dict[str, np.ndarray] | None = None
        if os.path.exists(self.model_path):
            self.load()

    @property
    def is_trained(self) -> bool:
        return bool(self.policy)

    def decide(
        self,
        context_id: str,
        network_state: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        demands = (network_state or {}).get("demands")
        if self.policy and context_id in self.policy:
            return self._action_to_allocation(context_id, self.policy[context_id], demands)
        return self.baseline.decide(context_id, demands)

    # Seeds of the fixed-context evaluation episodes: CEM samples are scored on
    # training seeds (common random numbers within an iteration), the returned
    # policy is selected on validation seeds and reported on held-out test seeds.
    TRAIN_SEED, VALIDATION_SEED, TEST_SEED = 0, 2000, 1000

    def train(
        self,
        episodes: int = 30,
        population: int = 16,
        elite_frac: float = 0.25,
        seed: int = 42,
        eval_episodes: int = 3,
        episode_steps: int = 24,
    ) -> dict[str, Any]:
        """CEM over log10 priority multipliers per context on the sequential env.

        ``episodes`` = CEM iterations. The environment, action space and reward
        are those of ``SequentialSlicingEnv`` (the shared reward), so this policy
        and PPO are trained and compared on identical semantics.
        """
        from scheduler.env_seq import SequentialSlicingEnv

        rng = np.random.default_rng(seed)
        env = SequentialSlicingEnv(capacity=self.baseline.total_bandwidth, episode_steps=episode_steps)
        n_elite = max(2, int(population * elite_frac))

        def score(context_id: str, action: np.ndarray, first_seed: int, n: int) -> float:
            total = 0.0
            for k in range(n):
                env.reset(seed=first_seed + k, options={"context": context_id})
                done = False
                while not done:
                    _, reward, _, done, _ = env.step(action)
                    total += reward
            return total / (n * episode_steps)

        policy: dict[str, np.ndarray] = {}
        per_context: dict[str, dict[str, float]] = {}
        curve: dict[str, list[float]] = {}
        for context_id in env.contexts:
            mean, std = np.zeros(4), np.full(4, 0.5)
            curve[context_id] = []
            for iteration in range(episodes):
                samples = np.clip(rng.normal(mean, std, size=(population, 4)), -1.0, 1.0)
                first = self.TRAIN_SEED + iteration * eval_episodes
                rewards = np.array([score(context_id, a, first, eval_episodes) for a in samples])
                elite = samples[np.argsort(rewards)[-n_elite:]]
                mean, std = elite.mean(axis=0), elite.std(axis=0) + 0.02
                curve[context_id].append(round(float(rewards.mean()), 3))

            rule_val = score(context_id, np.zeros(4), self.VALIDATION_SEED, 2 * eval_episodes)
            cem_val = score(context_id, mean, self.VALIDATION_SEED, 2 * eval_episodes)
            # Keep the rule-based priorities when the search does not beat them on validation.
            chosen = mean if cem_val > rule_val else np.zeros(4)
            policy[context_id] = 10 ** chosen
            per_context[context_id] = {
                "validation_baseline_reward": round(rule_val, 3),
                "validation_rl_reward": round(max(cem_val, rule_val), 3),
                "baseline_reward": round(score(context_id, np.zeros(4), self.TEST_SEED, 2 * eval_episodes), 3),
                "rl_reward": round(score(context_id, chosen, self.TEST_SEED, 2 * eval_episodes), 3),
                "kept_rule_based": bool(cem_val <= rule_val),
                "multipliers": {s: round(float(v), 3) for s, v in zip(SERVICE_CLASSES, policy[context_id])},
            }

        self.policy = policy
        self.save()

        rl_mean = float(np.mean([v["rl_reward"] for v in per_context.values()]))
        base_mean = float(np.mean([v["baseline_reward"] for v in per_context.values()]))
        return {
            "algorithm": "cross-entropy method over per-context log10 multipliers (SequentialSlicingEnv)",
            "iterations": episodes, "population": population, "seed": seed,
            "reward": "scheduler/reward.py (per-step mean over fixed-context episodes)",
            "contexts": len(per_context),
            "mean_rl_reward": round(rl_mean, 3),
            "mean_baseline_reward": round(base_mean, 3),
            "improvement": round(rl_mean - base_mean, 3),
            "evaluation": "held-out test seeds; selection on separate validation seeds",
            "per_context": per_context,
            "learning_curve": curve,
        }

    def _action_to_allocation(
        self,
        context_id: str,
        action: np.ndarray,
        demands: dict[str, float] | None = None,
    ) -> dict[str, float]:
        priorities = self.baseline.context_engine.get_context(context_id)
        if demands is None:
            demands = self.baseline.demand_generator.get_demands(context_id)
        action = np.clip(action, 0.1, 10.0)
        adjusted = {
            service: float(priorities.get(service, 1) * action[i])
            for i, service in enumerate(SERVICE_CLASSES)
        }
        return self.baseline.allocation_engine.allocate(
            self.baseline.total_bandwidth, adjusted, demands
        )

    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, "wb") as handle:
            pickle.dump({"policy": {k: v.tolist() for k, v in self.policy.items()}}, handle)

    def load(self):
        with open(self.model_path, "rb") as handle:
            data = pickle.load(handle)
        policy = data.get("policy")
        # Models from the earlier regressor-based trainer are not per-context policies.
        self.policy = (
            {k: np.array(v) for k, v in policy.items()} if isinstance(policy, dict) else None
        )


# --------------------------------------------------------------------------
# Priority policies for the live controller (PriorityEngine.policy)
# --------------------------------------------------------------------------

PPO_MODEL_PATH = os.path.join(MODEL_DIR, "ppo_slicing.zip")


class CEMPolicy:
    """Per-context multipliers learned by the CEM agent (contextual bandit)."""

    def __init__(self, agent: RLAgent | None = None):
        self.agent = agent or RLAgent()

    @property
    def available(self) -> bool:
        return self.agent.is_trained

    def __call__(self, context_id: str, state: dict[str, Any]) -> dict[str, float]:
        if not self.agent.policy or context_id not in self.agent.policy:
            return {s: 1.0 for s in SERVICE_CLASSES}
        action = np.clip(self.agent.policy[context_id], 0.1, 10.0)
        return {s: float(action[i]) for i, s in enumerate(SERVICE_CLASSES)}


class PPOPolicy:
    """PPO actor trained on the sequential environment; acts on live state."""

    def __init__(self, model_path: str = PPO_MODEL_PATH):
        self.model = None
        self.env = None
        if os.path.exists(model_path):
            from stable_baselines3 import PPO
            from scheduler.env_seq import SequentialSlicingEnv

            self.model = PPO.load(model_path, device="cpu")
            self.env = SequentialSlicingEnv()

    @property
    def available(self) -> bool:
        return self.model is not None

    def __call__(self, context_id: str, state: dict[str, Any]) -> dict[str, float]:
        if self.model is None:
            return {s: 1.0 for s in SERVICE_CLASSES}
        obs = self.env.observation_from_live(
            context_id,
            state.get("demands", {}),
            state.get("allocation", {}),
            state.get("backlog_bytes"),
            state.get("on_backup", False),
        )
        action, _ = self.model.predict(obs, deterministic=True)
        return self.env.action_to_multipliers(action)


class OnlineCEMPolicy:
    """CEM that keeps learning from live (Mininet) transitions.

    Per context it keeps a Gaussian over log10 multipliers, initialised from the
    simulator-trained CEM policy. Each controller decision samples an action
    (exploration); when the transition closes, its measured interval reward is
    credited to that action (``learn``). After ``population`` live samples of a
    context the mean moves to the elite actions and the spread shrinks. The
    state is checkpointed to ``ONLINE_PATH`` and resumed by the next run, so
    learning accumulates across runs.
    """

    ONLINE_PATH = os.path.join(MODEL_DIR, "cem_online.json")

    def __init__(self, path: str | None = None, population: int = 4, elite: int = 2,
                 init_std: float = 0.25, min_std: float = 0.05, seed: int = 0):
        import json

        # CARS_SF_CEM_ONLINE_PATH redirects the checkpoint (tests must not touch the deployed one).
        self.path = path or os.environ.get("CARS_SF_CEM_ONLINE_PATH") or self.ONLINE_PATH
        self.population, self.elite, self.min_std, self.init_std = population, elite, min_std, init_std
        self.rng = np.random.default_rng(seed)
        self.state: dict[str, dict[str, Any]] = {}
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as handle:
                self.state = json.load(handle)
        self.offline = RLAgent()
        self.updates_this_run = 0
        self.samples_this_run = 0

    available = True

    def _context(self, context_id: str) -> dict[str, Any]:
        if context_id not in self.state:
            prior = (self.offline.policy or {}).get(context_id)
            mean = np.log10(np.clip(prior, 0.1, 10.0)) if prior is not None else np.zeros(4)
            self.state[context_id] = {"mean": mean.tolist(), "std": [self.init_std] * 4,
                                      "batch": [], "updates": 0, "samples": 0}
        return self.state[context_id]

    def __call__(self, context_id: str, state: dict[str, Any]) -> dict[str, float]:
        ctx = self._context(context_id)
        action = np.clip(self.rng.normal(ctx["mean"], ctx["std"]), -1.0, 1.0)
        return {s: float(10 ** action[i]) for i, s in enumerate(SERVICE_CLASSES)}

    def learn(self, context_id: str, action: list[float], reward: float):
        ctx = self._context(context_id)
        ctx["batch"].append({"action": list(action), "reward": float(reward)})
        ctx["samples"] += 1
        self.samples_this_run += 1
        if len(ctx["batch"]) >= self.population:
            batch = sorted(ctx["batch"], key=lambda b: b["reward"])[-self.elite:]
            actions = np.array([b["action"] for b in batch])
            ctx["mean"] = actions.mean(axis=0).tolist()
            ctx["std"] = np.maximum(actions.std(axis=0), self.min_std).tolist()
            ctx["batch"] = []
            ctx["updates"] += 1
            self.updates_this_run += 1

    def save(self):
        import json

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)

    def learning_summary(self) -> dict[str, Any]:
        return {
            "algorithm": "online CEM on live transitions",
            "checkpoint": self.path,
            "samples_this_run": self.samples_this_run,
            "updates_this_run": self.updates_this_run,
            "per_context": {c: {"mean_log10": [round(v, 4) for v in st["mean"]], "updates": st["updates"],
                                "samples": st["samples"]} for c, st in self.state.items()},
        }


class OnlineResidualCEM(OnlineCEMPolicy):
    """Online CEM over the residual action (module D): starts at 0 (the QoS-aware
    heuristic itself) and learns per context from verified live transitions."""

    kind = "residual"
    ONLINE_PATH = os.path.join(MODEL_DIR, "cem_residual_online.json")

    def __init__(self, path: str | None = None, population: int = 4, elite: int = 2,
                 init_std: float = 0.3, min_std: float = 0.05, seed: int = 0, learning: bool = True):
        super().__init__(path=path or os.environ.get("CARS_SF_CEM_ONLINE_PATH") or self.ONLINE_PATH,
                         population=population, elite=elite, init_std=init_std, min_std=min_std, seed=seed)
        # learning=False: the same exploration (samples around a = 0) with updates disabled and
        # no checkpoint written: the control that isolates the effect of learning.
        self.learning = learning
        if not learning:
            self.state = {}

    def learn(self, context_id: str, action: list[float], reward: float):
        if self.learning:
            super().learn(context_id, action, reward)
        else:
            self.samples_this_run += 1

    def save(self):
        if self.learning:
            super().save()

    def _context(self, context_id: str) -> dict[str, Any]:
        if context_id not in self.state:
            self.state[context_id] = {"mean": [0.0] * 4, "std": [self.init_std] * 4,
                                      "batch": [], "updates": 0, "samples": 0}
        return self.state[context_id]

    def residual(self, context_id: str, obs) -> list[float]:
        ctx = self._context(context_id)
        return [float(a) for a in np.clip(self.rng.normal(ctx["mean"], ctx["std"]), -1.0, 1.0)]

    def learning_summary(self) -> dict[str, Any]:
        return {**super().learning_summary(), "learning": self.learning,
                "algorithm": "online CEM on residual actions (live transitions)"
                + ("" if self.learning else " — learning disabled")}


def train_ppo(timesteps: int = 200_000, seed: int = 0, model_path: str = PPO_MODEL_PATH,
              eval_every: int = 20_000, run_dir: str | None = None) -> dict[str, Any]:
    """Train PPO on the sequential env with a learning curve and checkpoints.

    Every ``eval_every`` steps the policy is scored deterministically on fixed
    *validation* seeds (VALIDATION_SEED…); the best checkpoint is kept. Final
    comparisons use the disjoint *test* seeds of ``evaluate_policy``.
    """
    import csv

    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.env_util import make_vec_env

    from scheduler.env_seq import SequentialSlicingEnv, evaluate_policy

    run_dir = run_dir or os.path.join(MODEL_DIR, "ppo_runs", f"seed{seed}")
    os.makedirs(run_dir, exist_ok=True)
    best_path = os.path.join(run_dir, "best.zip")
    curve: list[dict[str, Any]] = []

    class Curve(BaseCallback):
        def __init__(self):
            super().__init__()
            self.next_eval, self.best = eval_every, -float("inf")

        def _on_step(self) -> bool:
            if self.num_timesteps >= self.next_eval:
                self.next_eval += eval_every
                score = evaluate_policy(lambda o, e: self.model.predict(o, deterministic=True)[0],
                                        episodes=5, seed=RLAgent.VALIDATION_SEED)
                curve.append({"timesteps": self.num_timesteps, **score})
                self.model.save(os.path.join(run_dir, f"checkpoint_{self.num_timesteps}.zip"))
                if score["mean_reward"] > self.best:
                    self.best = score["mean_reward"]
                    self.model.save(best_path)
            return True

    vec_env = make_vec_env(lambda: SequentialSlicingEnv(), n_envs=8, seed=seed)
    model = PPO(
        "MlpPolicy", vec_env, seed=seed, verbose=0, device="cpu",
        n_steps=256, batch_size=512, learning_rate=3e-4, gamma=0.95, ent_coef=0.005,
    )
    model.learn(total_timesteps=timesteps, callback=Curve())
    if curve:
        with open(os.path.join(run_dir, "learning_curve.csv"), "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(curve[0]))
            writer.writeheader()
            writer.writerows(curve)
    best = PPO.load(best_path, device="cpu") if os.path.exists(best_path) else model
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    best.save(model_path)
    reloaded = PPO.load(model_path, device="cpu")     # the saved artifact is what gets evaluated
    return {
        "seed": seed, "timesteps": timesteps, "model_path": model_path, "run_dir": run_dir,
        "learning_curve": curve,
        "best_validation_reward": max((c["mean_reward"] for c in curve), default=None),
        "comparison": compare_policies(reloaded),
    }


def train_ppo_seeds(seeds: list[int], timesteps: int) -> dict[str, Any]:
    """Train one PPO per seed; deploy the one with the best *validation* score."""
    runs = [train_ppo(timesteps, seed=s, model_path=os.path.join(MODEL_DIR, "ppo_runs", f"seed{s}", "final.zip"))
            for s in seeds]
    best = max(runs, key=lambda r: r["best_validation_reward"] or -float("inf"))
    import shutil
    shutil.copy(best["model_path"], PPO_MODEL_PATH)
    test = [r["comparison"]["rl_ppo"]["mean_reward"] for r in runs]
    return {
        "seeds": seeds, "deployed_seed": best["seed"], "deployed_model": PPO_MODEL_PATH,
        "test_reward_per_seed": dict(zip(seeds, test)),
        "test_reward_mean": round(float(np.mean(test)), 2), "test_reward_std": round(float(np.std(test)), 2),
        "rule_based_test_reward": runs[0]["comparison"]["rule_based"]["mean_reward"],
        "rl_cem_test_reward": runs[0]["comparison"].get("rl_cem", {}).get("mean_reward"),
        "runs": runs,
    }


# --------------------------------------------------------------------------
# Residual policy (module D): corrections on top of the QoS-aware allocation
# --------------------------------------------------------------------------

RESIDUAL_MODEL_PATH = os.path.join(MODEL_DIR, "ppo_residual.zip")


# Held-out generalisation for the residual policy: medical_emergency is never seen in training,
# and evaluation also runs under a heavier workload than trained on.
RESIDUAL_TRAIN_CONTEXTS = ["normal", "school", "harvest", "disaster"]
RESIDUAL_HELDOUT = {"context": {"contexts": ["medical_emergency"]}, "load_1.3x": {"load_scale": 1.3}}
REWARD_VARIANTS = {"default": None, "sla_x2": {"sla": 20.0}, "loss_x4": {"loss": 2.0}}


def train_residual_ppo(timesteps: int = 300_000, seed: int = 0, eval_every: int = 25_000,
                       run_dir: str | None = None, env_kwargs: dict | None = None) -> dict[str, Any]:
    """PPO on DirectionalSlicingEnv; best checkpoint by validation reward (seeds 2000…)."""
    import csv

    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.env_util import make_vec_env

    from scheduler.env_dir import DirectionalSlicingEnv, evaluate_residual

    run_dir = run_dir or os.path.join(MODEL_DIR, "ppo_residual_runs", f"seed{seed}")
    os.makedirs(run_dir, exist_ok=True)
    best_path, curve = os.path.join(run_dir, "best.zip"), []

    class Curve(BaseCallback):
        def __init__(self):
            super().__init__()
            self.next_eval, self.best = eval_every, -float("inf")

        def _on_step(self) -> bool:
            if self.num_timesteps >= self.next_eval:
                self.next_eval += eval_every
                score = evaluate_residual(lambda o, e: self.model.predict(o, deterministic=True)[0],
                                          episodes=5, seed=RLAgent.VALIDATION_SEED, **(env_kwargs or {}))
                curve.append({"timesteps": self.num_timesteps,
                              **{k: v for k, v in score.items() if k not in ("episode_rewards", "mean_loss_pct")}})
                self.model.save(os.path.join(run_dir, f"checkpoint_{self.num_timesteps}.zip"))
                if score["mean_reward"] > self.best:
                    self.best = score["mean_reward"]
                    self.model.save(best_path)
            return True

    vec_env = make_vec_env(lambda: DirectionalSlicingEnv(**(env_kwargs or {})), n_envs=8, seed=seed)
    model = PPO("MlpPolicy", vec_env, seed=seed, verbose=0, device="cpu",
                n_steps=256, batch_size=512, learning_rate=3e-4, gamma=0.9, ent_coef=0.0)
    model.learn(total_timesteps=timesteps, callback=Curve())
    if curve:
        with open(os.path.join(run_dir, "learning_curve.csv"), "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(curve[0]))
            writer.writeheader()
            writer.writerows(curve)
    final = os.path.join(run_dir, "final.zip")
    (PPO.load(best_path, device="cpu") if os.path.exists(best_path) else model).save(final)
    return {"seed": seed, "timesteps": timesteps, "model_path": final, "learning_curve": curve,
            "best_validation_reward": max((c["mean_reward"] for c in curve), default=None)}


def compare_residual(model=None, episodes: int = 30, env_kwargs: dict | None = None) -> dict[str, Any]:
    """Heuristic (zero residual) vs the residual PPO on held-out test seeds, paired."""
    import numpy as np

    from scheduler.env_dir import evaluate_residual

    kw = env_kwargs or {}
    results = {"qos_heuristic": evaluate_residual(lambda o, e: np.zeros(4), episodes, **kw)}
    if model is not None:
        results["rl_residual"] = evaluate_residual(lambda o, e: model.predict(o, deterministic=True)[0], episodes, **kw)
        results["paired_vs_heuristic"] = paired_difference(results["rl_residual"]["episode_rewards"],
                                                           results["qos_heuristic"]["episode_rewards"])
    return results


def train_residual_seeds(seeds: list[int], timesteps: int, variant: str = "default") -> dict[str, Any]:
    """Train one residual PPO per seed on the training contexts with the variant's reward weights;
    evaluate on held-out test seeds, the held-out context and a heavier workload. Only the
    default variant is deployed."""
    import shutil

    from stable_baselines3 import PPO

    weights = REWARD_VARIANTS[variant]
    train_kwargs = {"contexts": RESIDUAL_TRAIN_CONTEXTS, "reward_weights": weights}
    root = os.path.join(MODEL_DIR, "ppo_residual_runs" if variant == "default" else f"ppo_residual_{variant}_runs")
    runs = [train_residual_ppo(timesteps, seed=s, run_dir=os.path.join(root, f"seed{s}"), env_kwargs=train_kwargs)
            for s in seeds]
    for run in runs:
        model = PPO.load(run["model_path"], device="cpu")
        run["comparison"] = compare_residual(model, env_kwargs=train_kwargs)
        run["heldout"] = {name: compare_residual(model, env_kwargs={**kw, "reward_weights": weights})
                          for name, kw in RESIDUAL_HELDOUT.items()}
    best = max(runs, key=lambda r: r["best_validation_reward"] or -float("inf"))
    if variant == "default":
        shutil.copy(best["model_path"], RESIDUAL_MODEL_PATH)
    test = [r["comparison"]["rl_residual"]["mean_reward"] for r in runs]
    return {
        "variant": variant, "reward_weights": weights, "train_contexts": RESIDUAL_TRAIN_CONTEXTS,
        "heldout_paired": {name: {r["seed"]: r["heldout"][name]["paired_vs_heuristic"] for r in runs}
                           for name in RESIDUAL_HELDOUT},
        "seeds": seeds, "deployed_seed": best["seed"],
        "deployed_model": RESIDUAL_MODEL_PATH if variant == "default" else None,
        "test_reward_per_seed": dict(zip(seeds, test)),
        "heuristic_test_reward": runs[0]["comparison"]["qos_heuristic"]["mean_reward"],
        "paired_per_seed": {r["seed"]: r["comparison"]["paired_vs_heuristic"] for r in runs},
        "runs": runs,
    }


class ResidualPPOPolicy:
    """Live residual policy: PPO action on state v2, applied by the controller."""

    kind = "residual"

    def __init__(self, model_path: str = RESIDUAL_MODEL_PATH):
        self.model = None
        if os.path.exists(model_path):
            from stable_baselines3 import PPO
            self.model = PPO.load(model_path, device="cpu")

    @property
    def available(self) -> bool:
        return self.model is not None

    def residual(self, context_id: str, obs) -> list[float]:
        action, _ = self.model.predict(obs, deterministic=True)
        return [float(a) for a in action]


class ClosedLoopResidualPolicy(OnlineResidualCEM):
    """The closed loop's agent: the simulator-trained PPO proposes a correction from the
    current state; an online CEM layer adds a per-context offset learned from verified live
    transitions. ``state`` is the observation the deployed PPO was trained on."""

    ONLINE_PATH = os.path.join(MODEL_DIR, "closed_loop_online.json")
    MODEL_PATH = os.path.join(MODEL_DIR, "ppo_closed_loop.zip")
    METADATA_PATH = os.path.join(MODEL_DIR, "ppo_closed_loop.json")

    def __init__(self, path: str | None = None, seed: int = 0, learning: bool = True):
        super().__init__(path=path or os.environ.get("CARS_SF_CEM_ONLINE_PATH") or self.ONLINE_PATH,
                         init_std=0.15, seed=seed, learning=learning)
        self.model = None
        self.state_version = "v2"
        if os.path.exists(self.MODEL_PATH):
            import json

            from stable_baselines3 import PPO
            self.model = PPO.load(self.MODEL_PATH, device="cpu")
            with open(self.METADATA_PATH, encoding="utf-8") as handle:
                self.state_version = json.load(handle)["state"]
        self._offsets: dict[tuple, list[float]] = {}

    @property
    def available(self) -> bool:
        return self.model is not None

    def residual(self, context_id: str, obs) -> list[float]:
        offset = super().residual(context_id, obs)
        base, _ = self.model.predict(obs, deterministic=True)
        action = [float(a) for a in np.clip(np.asarray(base) + np.asarray(offset), -1.0, 1.0)]
        self._offsets[tuple(round(a, 4) for a in action)] = offset      # transitions log rounded actions
        return action

    def learn(self, context_id: str, action: list[float], reward: float):
        offset = self._offsets.pop(tuple(round(a, 4) for a in action), None)
        if offset is not None:
            super().learn(context_id, offset, reward)


def compare_policies(model=None, episodes: int = 30) -> dict[str, Any]:
    from scheduler.env_seq import SequentialSlicingEnv, evaluate_policy

    cem = CEMPolicy()
    probe_env = SequentialSlicingEnv()

    def rule(obs, env):
        return np.zeros(4)

    def cem_policy(obs, env):
        mult = cem(env.context, {})
        return np.log10(np.clip([mult[s] for s in SERVICE_CLASSES], 0.1, 10.0))

    results = {"rule_based": evaluate_policy(rule, episodes)}
    if cem.available:
        results["rl_cem"] = evaluate_policy(cem_policy, episodes)
    if model is not None:
        results["rl_ppo"] = evaluate_policy(
            lambda obs, env: model.predict(obs, deterministic=True)[0], episodes
        )
    results["contexts"] = probe_env.contexts
    results["paired_vs_rule_based"] = {
        name: paired_difference(results[name]["episode_rewards"], results["rule_based"]["episode_rewards"])
        for name in ("rl_cem", "rl_ppo") if name in results
    }
    return results


def paired_difference(a: list[float], b: list[float]) -> dict[str, Any]:
    """Same evaluation seeds → paired episodes: mean difference, 95% CI, Wilcoxon p."""
    from scipy import stats

    diff = np.asarray(a) - np.asarray(b)
    half = stats.t.ppf(0.975, len(diff) - 1) * diff.std(ddof=1) / np.sqrt(len(diff)) if len(diff) > 1 else float("nan")
    p_value = float(stats.wilcoxon(diff).pvalue) if np.any(diff != 0) else 1.0
    return {
        "episodes": int(len(diff)), "mean_diff": round(float(diff.mean()), 3),
        "ci95": [round(float(diff.mean() - half), 3), round(float(diff.mean() + half), 3)],
        "relative_pct": round(float(diff.mean() / np.mean(b) * 100), 3),
        "wilcoxon_p": round(p_value, 6), "wins": int((diff > 0).sum()), "losses": int((diff < 0).sum()),
    }

"""
SliceNet: service-class identification from traffic shape.

  SliceNetClassifier  random forest on tabular features (shape_* columns when
                      present, i.e. Mininet data; the RSNSD-compatible ML
                      columns otherwise, i.e. the synthetic baseline)
  SliceNetCNN         1D-CNN over the first 32 packets of a flow window
                      (signed size, log inter-arrival, TCP control) fused with
                      the shape-feature vector — the "SliceNet CNN" of the
                      literature, implemented in PyTorch

Evaluation always holds out whole groups (run × UE for measured data, RSNSD
scenario for synthetic data) so a model is scored on traffic from runs,
devices or scenarios it never saw.

Inference has an explicit fallback policy: a window whose top-class
probability is below ``CONFIDENCE_THRESHOLD`` (or whose features are not
finite) is *abstained* on, and callers route it to ``FALLBACK_CLASS``
(best effort) or defer the decision. Without a trained model nothing is
predicted; ground-truth labels are never substituted for predictions.
"""

from __future__ import annotations

import os
import pickle
from typing import Any

import numpy as np
import pandas as pd

from core.config import REPO_ROOT, load_features
from features.schema_mapper import EXCLUDED_FROM_ML, ML_FEATURE_COLUMNS
from features.shape import SEQ_CHANNELS, SEQ_LEN, SHAPE_FEATURES

SERVICE_CLASSES = ["healthcare", "education", "agriculture", "general"]
MODEL_DIR = REPO_ROOT / "classification" / "models"
SHAPE_COLUMNS = [f"shape_{c}" for c in SHAPE_FEATURES]
CONFIDENCE_THRESHOLD = 0.5
FALLBACK_CLASS = "general"


class ModelNotTrained(RuntimeError):
    pass


def feature_columns_for(df: pd.DataFrame) -> list[str]:
    shape = [c for c in SHAPE_COLUMNS if c in df.columns]
    if shape:
        return shape
    return [c for c in ML_FEATURE_COLUMNS if c in df.columns and c not in EXCLUDED_FROM_ML]


def group_labels(df: pd.DataFrame) -> np.ndarray:
    if "rsnsd_scenario" in df.columns:
        return df["rsnsd_scenario"].astype(str).to_numpy()
    if "run_id" in df.columns and "ue_host" in df.columns:
        return (df["run_id"].astype(str) + "/" + df["ue_host"].astype(str)).to_numpy()
    if "ue_host" in df.columns:
        return df["ue_host"].astype(str).to_numpy()
    return np.arange(len(df))


def has_group_keys(df: pd.DataFrame) -> bool:
    return "ue_host" in df.columns or "run_id" in df.columns or "rsnsd_scenario" in df.columns


def split_description(df: pd.DataFrame) -> str:
    if has_group_keys(df) and len(set(group_labels(df))) >= 4:
        return "group (RSNSD scenario held out)" if "rsnsd_scenario" in df.columns else "group (run × UE held out)"
    return "random row split (dataset has no run/UE/scenario keys)"


def group_split(df: pd.DataFrame, test_size: float, seed: int = 42):
    from sklearn.model_selection import GroupShuffleSplit, train_test_split

    groups = group_labels(df)
    if len(set(groups)) >= 4:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        return next(splitter.split(df, groups=groups))
    idx = np.arange(len(df))
    return train_test_split(idx, test_size=test_size, random_state=seed, stratify=df["service_class"])


def _metrics(y_true, y_pred) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

    labels = list(range(len(SERVICE_CLASSES)))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", labels=labels, zero_division=0)),
        "report": classification_report(
            y_true, y_pred, labels=labels, target_names=SERVICE_CLASSES,
            output_dict=True, zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def _selective(proba: np.ndarray, y_true: np.ndarray, threshold: float = CONFIDENCE_THRESHOLD) -> dict[str, Any]:
    """Held-out effect of the abstention policy: how often it abstains and how
    accurate the accepted decisions are."""
    accepted = proba.max(axis=1) >= threshold
    pred = proba.argmax(axis=1)
    return {
        "confidence_threshold": threshold,
        "abstention_rate": round(float(1 - accepted.mean()), 4) if len(y_true) else None,
        "accepted_accuracy": round(float((pred[accepted] == y_true[accepted]).mean()), 4) if accepted.any() else None,
    }


def _decisions(proba: np.ndarray, classes: list[str], finite: np.ndarray, threshold: float) -> list[dict[str, Any]]:
    out = []
    for row, ok in zip(proba, finite):
        best = int(np.argmax(row))
        confidence = float(row[best])
        abstained = (not ok) or confidence < threshold
        out.append({
            "predicted": classes[best], "confidence": round(confidence, 4), "abstained": bool(abstained),
            "reason": None if not abstained else ("invalid_features" if not ok else "low_confidence"),
        })
    return out


class SliceNetClassifier:
    """Tabular SliceNet (random forest)."""

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or str(MODEL_DIR / "slicenet_model.pkl")
        self.feature_columns: list[str] = []
        self.excluded = list(EXCLUDED_FROM_ML) + load_features().get("excluded_from_ml", [])
        self.model = None
        self.label_encoder: dict[str, int] = {c: i for i, c in enumerate(SERVICE_CLASSES)}
        self.inverse_encoder = {i: c for c, i in self.label_encoder.items()}
        if os.path.exists(self.model_path):
            self.load()

    def _get_feature_matrix(self, df) -> np.ndarray:
        cols = self.feature_columns or feature_columns_for(df)
        frame = pd.DataFrame({c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else 0.0 for c in cols})
        return frame.fillna(0).to_numpy(dtype=float)

    def train(self, df, test_size: float = 0.2, seed: int = 42) -> dict[str, Any]:
        from sklearn.ensemble import RandomForestClassifier

        if "service_class" not in df.columns:
            raise ValueError("Dataset must contain 'service_class' label column")
        df = df[df["service_class"].isin(SERVICE_CLASSES)].reset_index(drop=True)
        self.feature_columns = feature_columns_for(df)
        X = self._get_feature_matrix(df)
        y = df["service_class"].map(self.label_encoder).to_numpy()
        train_idx, test_idx = group_split(df, test_size, seed)

        self.model = RandomForestClassifier(
            n_estimators=200, max_depth=16, random_state=seed, n_jobs=-1, class_weight="balanced"
        )
        self.model.fit(X[train_idx], y[train_idx])
        metrics = _metrics(y[test_idx], self.model.predict(X[test_idx]))
        metrics.update(_selective(self.model.predict_proba(X[test_idx]), y[test_idx]))
        metrics.update({
            "model": "random_forest",
            "train_size": int(len(train_idx)),
            "test_size": int(len(test_idx)),
            "feature_count": len(self.feature_columns),
            "split": split_description(df),
            "feature_importance": dict(sorted(
                zip(self.feature_columns, self.model.feature_importances_.round(4).tolist()),
                key=lambda kv: -kv[1],
            )[:10]),
        })
        self.save()
        return metrics

    def evaluate(self, df) -> dict[str, Any]:
        df = df[df["service_class"].isin(SERVICE_CLASSES)]
        y = df["service_class"].map(self.label_encoder).to_numpy()
        return _metrics(y, self.model.predict(self._get_feature_matrix(df)))

    def predict(self, features: dict[str, Any]) -> str:
        return self.predict_batch(pd.DataFrame([features]))[0]

    def predict_batch(self, df) -> list[str]:
        if self.model is None:
            raise ModelNotTrained(f"no trained SliceNet model at {self.model_path}")
        preds = self.model.predict(self._get_feature_matrix(df))
        return [self.inverse_encoder.get(int(p), FALLBACK_CLASS) for p in preds]

    def predict_with_confidence(self, df, threshold: float = CONFIDENCE_THRESHOLD) -> list[dict[str, Any]]:
        """Per row: predicted class, top probability and whether SliceNet abstained."""
        if self.model is None:
            raise ModelNotTrained(f"no trained SliceNet model at {self.model_path}")
        cols = self.feature_columns or feature_columns_for(df)
        raw = pd.DataFrame({c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else np.nan for c in cols})
        finite = np.isfinite(raw.to_numpy(dtype=float)).all(axis=1)
        proba = self.model.predict_proba(raw.replace([np.inf, -np.inf], np.nan).fillna(0).to_numpy(dtype=float))
        classes = [self.inverse_encoder.get(int(c), FALLBACK_CLASS) for c in self.model.classes_]
        return _decisions(proba, classes, finite, threshold)

    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, "wb") as handle:
            pickle.dump({
                "model": self.model,
                "feature_columns": self.feature_columns,
                "label_encoder": self.label_encoder,
            }, handle)

    def load(self):
        with open(self.model_path, "rb") as handle:
            data = pickle.load(handle)
        self.model = data["model"]
        self.feature_columns = data.get("feature_columns", [])
        self.label_encoder = data.get("label_encoder", self.label_encoder)
        self.inverse_encoder = {i: c for c, i in self.label_encoder.items()}


# --------------------------------------------------------------------------
# 1D-CNN
# --------------------------------------------------------------------------

CNN_MODEL_PATH = MODEL_DIR / "slicenet_cnn.pt"


def _build_cnn(n_shape: int):
    import torch
    from torch import nn

    class SliceNetCNNModule(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv1d(SEQ_CHANNELS, 32, kernel_size=3, padding=1), nn.BatchNorm1d(32), nn.ReLU(),
                nn.Conv1d(32, 64, kernel_size=3, padding=1), nn.BatchNorm1d(64), nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Conv1d(64, 64, kernel_size=3, padding=1), nn.BatchNorm1d(64), nn.ReLU(),
                nn.AdaptiveAvgPool1d(1),
            )
            self.shape = nn.Sequential(nn.Linear(n_shape, 64), nn.ReLU())
            self.head = nn.Sequential(nn.Dropout(0.3), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, len(SERVICE_CLASSES)))

        def forward(self, seq, shape):
            return self.head(torch.cat([self.conv(seq).squeeze(-1), self.shape(shape)], dim=1))

    return SliceNetCNNModule()


class SliceNetCNN:
    def __init__(self, model_path: str | os.PathLike = CNN_MODEL_PATH):
        self.model_path = str(model_path)
        self.model = None
        self.mean = self.std = None
        self.shape_columns = [c for c in SHAPE_COLUMNS]
        if os.path.exists(self.model_path):
            self.load()

    def _shape_matrix(self, df) -> np.ndarray:
        X = df.reindex(columns=self.shape_columns).apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(dtype=np.float32)
        X = np.sign(X) * np.log1p(np.abs(X))
        return (X - self.mean) / self.std

    def train(self, df, sequences: np.ndarray, test_size: float = 0.2, seed: int = 42, epochs: int = 80,
              val_size: float = 0.15, patience: int = 10) -> dict[str, Any]:
        import torch
        from torch import nn

        torch.manual_seed(seed)
        keep = df["service_class"].isin(SERVICE_CLASSES).to_numpy()
        df, sequences = df[keep].reset_index(drop=True), sequences[keep]
        y = df["service_class"].map({c: i for i, c in enumerate(SERVICE_CLASSES)}).to_numpy()
        train_idx, test_idx = group_split(df, test_size, seed)
        # Validation groups are carved out of the training groups (never the test
        # groups) and drive early stopping; the test split is scored once at the end.
        inner_train, inner_val = group_split(df.iloc[train_idx].reset_index(drop=True), val_size, seed + 1)
        train_idx, val_idx = train_idx[inner_train], train_idx[inner_val]

        raw = df.reindex(columns=self.shape_columns).apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(dtype=np.float32)
        raw = np.sign(raw) * np.log1p(np.abs(raw))
        self.mean = raw[train_idx].mean(axis=0)
        self.std = raw[train_idx].std(axis=0) + 1e-6
        shape = (raw - self.mean) / self.std

        self.model = _build_cnn(shape.shape[1])
        seq_t = torch.tensor(sequences, dtype=torch.float32)
        shape_t = torch.tensor(shape, dtype=torch.float32)
        y_t = torch.tensor(y, dtype=torch.long)
        counts = np.bincount(y[train_idx], minlength=len(SERVICE_CLASSES)).astype(float)
        weights = torch.tensor(counts.sum() / np.maximum(counts, 1) / len(counts), dtype=torch.float32)
        loss_fn = nn.CrossEntropyLoss(weight=weights)
        optim = torch.optim.Adam(self.model.parameters(), lr=1e-3, weight_decay=1e-4)
        history, val_history = [], []
        best_val, best_state, best_epoch, stale = float("inf"), None, 0, 0
        rng = np.random.default_rng(seed)
        for epoch in range(epochs):
            self.model.train()
            order = rng.permutation(train_idx)
            total = 0.0
            for start in range(0, len(order), 128):
                batch = order[start:start + 128]
                optim.zero_grad()
                loss = loss_fn(self.model(seq_t[batch], shape_t[batch]), y_t[batch])
                loss.backward()
                optim.step()
                total += loss.item() * len(batch)
            history.append(round(total / max(len(train_idx), 1), 4))
            self.model.eval()
            with torch.no_grad():
                val_loss = loss_fn(self.model(seq_t[val_idx], shape_t[val_idx]), y_t[val_idx]).item()
            val_history.append(round(val_loss, 4))
            if val_loss < best_val - 1e-4:
                best_val, best_epoch, stale = val_loss, epoch, 0
                best_state = {k: v.detach().clone() for k, v in self.model.state_dict().items()}
            else:
                stale += 1
                if stale >= patience:
                    break
        if best_state is not None:
            self.model.load_state_dict(best_state)

        self.model.eval()
        with torch.no_grad():
            preds = self.model(seq_t[test_idx], shape_t[test_idx]).argmax(dim=1).numpy()
            proba = torch.softmax(self.model(seq_t[test_idx], shape_t[test_idx]), dim=1).numpy()
        metrics = _metrics(y[test_idx], preds)
        metrics.update(_selective(proba, y[test_idx]))
        metrics.update({
            "model": "cnn_1d",
            "train_size": int(len(train_idx)),
            "val_size": int(len(val_idx)),
            "test_size": int(len(test_idx)),
            "epochs": epochs,
            "epochs_run": len(history),
            "best_epoch": best_epoch + 1,
            "loss_history": history,
            "val_loss_history": val_history,
            "split": split_description(df) + ", validation groups carved from training groups",
            "sequence_length": SEQ_LEN,
        })
        self.save()
        return metrics

    def _proba(self, df, sequences: np.ndarray) -> np.ndarray:
        import torch

        if self.model is None:
            raise ModelNotTrained(f"no trained SliceNet CNN at {self.model_path}")
        with torch.no_grad():
            logits = self.model(
                torch.tensor(sequences, dtype=torch.float32),
                torch.tensor(self._shape_matrix(df), dtype=torch.float32),
            )
        return torch.softmax(logits, dim=1).numpy()

    def predict_batch(self, df, sequences: np.ndarray) -> list[str]:
        return [SERVICE_CLASSES[i] for i in self._proba(df, sequences).argmax(axis=1)]

    def predict_with_confidence(self, df, sequences: np.ndarray,
                                threshold: float = CONFIDENCE_THRESHOLD) -> list[dict[str, Any]]:
        raw = df.reindex(columns=self.shape_columns).apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(raw).all(axis=1) & np.isfinite(sequences).reshape(len(sequences), -1).all(axis=1)
        return _decisions(self._proba(df, np.nan_to_num(sequences)), SERVICE_CLASSES, finite, threshold)

    def save(self):
        import torch

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save({
            "state_dict": self.model.state_dict(),
            "mean": self.mean, "std": self.std,
            "shape_columns": self.shape_columns,
        }, self.model_path)

    def load(self):
        import torch

        data = torch.load(self.model_path, weights_only=False)
        self.shape_columns = data["shape_columns"]
        self.mean, self.std = data["mean"], data["std"]
        self.model = _build_cnn(len(self.shape_columns))
        self.model.load_state_dict(data["state_dict"])
        self.model.eval()

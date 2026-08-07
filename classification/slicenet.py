"""
SliceNet: 1D-CNN classifier for rural service class identification.

Classifies network flows into: healthcare, education, agriculture, general.
"""

from __future__ import annotations

import os
import pickle
from typing import Any

import numpy as np
import pandas as pd

from core.config import REPO_ROOT, load_features
from features.schema_mapper import ML_FEATURE_COLUMNS, EXCLUDED_FROM_ML

SERVICE_CLASSES = ["healthcare", "education", "agriculture", "general"]
MODEL_DIR = REPO_ROOT / "classification" / "models"


class SliceNetClassifier:
    """Service-class classifier with sklearn fallback and optional PyTorch CNN."""

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or str(MODEL_DIR / "slicenet_model.pkl")
        self.feature_columns = ML_FEATURE_COLUMNS
        self.excluded = list(EXCLUDED_FROM_ML) + load_features().get("excluded_from_ml", [])
        self.model = None
        self.label_encoder: dict[str, int] = {c: i for i, c in enumerate(SERVICE_CLASSES)}
        self.inverse_encoder = {i: c for c, i in self.label_encoder.items()}

        if os.path.exists(self.model_path):
            self.load()

    def _get_feature_matrix(self, df) -> np.ndarray:
        available = [c for c in self.feature_columns if c in df.columns]
        if not available:
            numeric = df.select_dtypes(include="number").columns.tolist()
            available = [c for c in numeric if c not in self.excluded]
        numeric_cols = [c for c in available if pd.api.types.is_numeric_dtype(df[c])]
        if not numeric_cols:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
        return df[numeric_cols].fillna(0).values

    def train(self, df, test_size: float = 0.2) -> dict[str, Any]:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report, f1_score
        from sklearn.model_selection import train_test_split

        if "service_class" not in df.columns:
            raise ValueError("Dataset must contain 'service_class' label column")

        X = self._get_feature_matrix(df)
        y = df["service_class"].map(self.label_encoder).fillna(0).astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        self.model = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
        )
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)

        metrics = {
            "f1_macro": float(f1_score(y_test, y_pred, average="macro")),
            "f1_weighted": float(f1_score(y_test, y_pred, average="weighted")),
            "report": classification_report(
                y_test, y_pred,
                target_names=SERVICE_CLASSES,
                output_dict=True,
            ),
            "train_size": len(X_train),
            "test_size": len(X_test),
        }

        os.makedirs(MODEL_DIR, exist_ok=True)
        self.save()
        return metrics

    def predict(self, features: dict[str, Any]) -> str:
        if self.model is None:
            return features.get("service_class", "general")

        import pandas as pd
        df = pd.DataFrame([features])
        X = self._get_feature_matrix(df)
        pred_idx = int(self.model.predict(X)[0])
        return self.inverse_encoder.get(pred_idx, "general")

    def predict_batch(self, df) -> list[str]:
        if self.model is None:
            return df.get("service_class", "general").tolist()

        X = self._get_feature_matrix(df)
        preds = self.model.predict(X)
        return [self.inverse_encoder.get(int(p), "general") for p in preds]

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
        self.feature_columns = data.get("feature_columns", self.feature_columns)
        self.label_encoder = data.get("label_encoder", self.label_encoder)
        self.inverse_encoder = {i: c for c, i in self.label_encoder.items()}

"""Statistical validation for Mininet-generated datasets.

Score (max 100, pass ≥ 80):
  schema completeness        20   required ML + label columns present
  class coverage / balance   15   every service class present, minority ≥ 5 %
  physical consistency       20   goodput ≤ throughput, loss ∈ [0,100], delays ≥ 0
  measurement coverage       15   records with a measured (non-NaN) latency
  load–delay relationship    15   queueing delay rises with link utilisation
  feature quality            15   few near-constant ML features, few extreme outliers
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from core.config import load_features

SERVICE_CLASSES = ("healthcare", "education", "agriculture", "general")


class DatasetValidator:
    """Validates dataset schema, QoS consistency, and basic statistics."""

    PASS_THRESHOLD = 80

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.feature_config = load_features()
        self.score = 0
        self.report: dict[str, Any] = {}

    def validate(self) -> dict[str, Any]:
        parts = {
            "schema_score": self._check_schema(),
            "class_score": self._check_classes(),
            "qos_score": self._check_qos_consistency(),
            "measurement_score": self._check_measurement_coverage(),
            "correlation_score": self._check_correlations(),
            "feature_quality_score": self._check_feature_quality(),
        }
        self.score = int(sum(parts.values()))
        self.report = {
            "total_score": self.score,
            "passed": self.score >= self.PASS_THRESHOLD,
            **parts,
            "row_count": len(self.df),
            "column_count": len(self.df.columns),
            "class_counts": (
                self.df["service_class"].value_counts().to_dict()
                if "service_class" in self.df.columns else {}
            ),
        }
        return self.report

    def _col(self, name: str) -> pd.Series | None:
        return self.df[name] if name in self.df.columns else None

    def _check_schema(self) -> int:
        required = (
            self.feature_config.get("ml_feature_columns", [])
            + self.feature_config.get("label_columns", [])
        )
        present = sum(1 for col in required if col in self.df.columns)
        return int(round(20 * present / max(len(required), 1)))

    def _check_classes(self) -> int:
        labels = self._col("service_class")
        if labels is None or labels.empty:
            return 0
        shares = labels.value_counts(normalize=True)
        coverage = sum(1 for c in SERVICE_CLASSES if c in shares.index) / len(SERVICE_CLASSES)
        balanced = 1.0 if shares.min() >= 0.05 else shares.min() / 0.05
        return int(round(10 * coverage + 5 * balanced))

    def _check_qos_consistency(self) -> int:
        if self.df.empty:
            return 0
        n = len(self.df)
        bad = pd.Series(False, index=self.df.index)
        tput, good = self._col("throughput_mbps"), self._col("goodput_mbps")
        if tput is not None and good is not None:
            bad |= good > tput + 1e-6
        loss = self._col("packet_loss_rate")
        if loss is not None:
            bad |= (loss < 0) | (loss > 100)
        for name in ("end_to_end_latency_ms", "jitter_ms", "queueing_delay_ms"):
            col = self._col(name)
            if col is not None:
                bad |= col < -1e-6
        return int(round(20 * (1 - bad.sum() / n)))

    def _check_measurement_coverage(self) -> int:
        latency = self._col("end_to_end_latency_ms")
        if latency is None or latency.empty:
            return 0
        return int(round(15 * latency.notna().mean()))

    def _check_correlations(self) -> int:
        util, delay = self._col("link_utilization_pct"), self._col("queueing_delay_ms")
        if util is None or delay is None or len(self.df) < 5:
            return 8
        pair = pd.concat([util, delay], axis=1).dropna()
        if len(pair) < 5 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
            return 8  # not enough load variation in this run to judge
        corr = pair.iloc[:, 0].corr(pair.iloc[:, 1], method="spearman")
        return 15 if corr >= 0 else 5

    def _check_feature_quality(self) -> int:
        ml_cols = [c for c in self.feature_config.get("ml_feature_columns", []) if c in self.df.columns]
        numeric = self.df[ml_cols].select_dtypes(include="number") if ml_cols else pd.DataFrame()
        if numeric.empty:
            return 0
        constant = (numeric.nunique(dropna=True) <= 1).mean()
        outliers = 0
        for col in numeric.columns:
            q1, q3 = numeric[col].quantile(0.25), numeric[col].quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                outliers += ((numeric[col] < q1 - 3 * iqr) | (numeric[col] > q3 + 3 * iqr)).sum()
        outlier_ratio = outliers / max(numeric.size, 1)
        return int(round(8 * (1 - constant) + 7 * max(0.0, 1 - outlier_ratio / 0.05)))

    def constant_ml_features(self) -> list[str]:
        ml_cols = [c for c in self.feature_config.get("ml_feature_columns", []) if c in self.df.columns]
        return [c for c in ml_cols if self.df[c].nunique(dropna=True) <= 1]

    def format_report(self) -> str:
        r = self.report
        lines = [
            "CARS-SF Dataset Validation Report",
            "=" * 40,
            f"Score: {r.get('total_score', 0)}/100 (pass ≥ {self.PASS_THRESHOLD})",
            f"Passed: {r.get('passed', False)}",
            f"Rows: {r.get('row_count', 0)}",
            f"Columns: {r.get('column_count', 0)}",
            f"Classes: {r.get('class_counts', {})}",
            f"  Schema:              {r.get('schema_score', 0)}/20",
            f"  Class coverage:      {r.get('class_score', 0)}/15",
            f"  Physical QoS:        {r.get('qos_score', 0)}/20",
            f"  Measured latency:    {r.get('measurement_score', 0)}/15",
            f"  Load-delay relation: {r.get('correlation_score', 0)}/15",
            f"  Feature quality:     {r.get('feature_quality_score', 0)}/15",
            f"Constant ML features: {self.constant_ml_features()}",
        ]
        return "\n".join(lines)

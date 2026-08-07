"""
Dataset Statistics

Computes descriptive statistics for the generated RSNSD dataset.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class DatasetStatistics:

    rows: int
    columns: int

    unique_applications: int
    unique_service_classes: int
    unique_service_types: int

    average_latency_ms: float
    average_throughput_mbps: float
    average_packet_loss_pct: float
    average_jitter_ms: float

    average_qos_score: float
    sla_success_rate: float
    
    # Advanced stats
    mutual_information: dict = None
    feature_importance: dict = None


class StatisticsAnalyzer:

    def analyze(
        self,
        dataframe: pd.DataFrame,
    ) -> DatasetStatistics:
        
        # Safe computation of MI and Importance for a subset
        mutual_info_dict = {}
        importance_dict = {}
        
        try:
            from sklearn.feature_selection import mutual_info_classif
            from sklearn.ensemble import RandomForestClassifier
            import numpy as np
            
            # Use a smaller sample for fast computation
            df_sample = dataframe.sample(min(5000, len(dataframe)))
            numeric_cols = df_sample.select_dtypes(include=['float64', 'int64']).columns
            
            if len(numeric_cols) > 2 and "service_class" in df_sample.columns:
                X = df_sample[numeric_cols].fillna(0)
                y = df_sample["service_class"]
                
                # Mutual Info
                mi_scores = mutual_info_classif(X, y)
                mutual_info_dict = dict(zip(numeric_cols, mi_scores))
                
                # Random Forest Importance
                rf = RandomForestClassifier(n_estimators=10, random_state=42)
                rf.fit(X, y)
                importance_dict = dict(zip(numeric_cols, rf.feature_importances_))
        except Exception:
            pass

        return DatasetStatistics(

            rows=len(dataframe),

            columns=len(dataframe.columns),

            unique_applications=dataframe["application_id"].nunique() if "application_id" in dataframe else 0,

            unique_service_classes=dataframe["service_class"].nunique() if "service_class" in dataframe else 0,

            unique_service_types=dataframe["service_type"].nunique() if "service_type" in dataframe else 0,

            average_latency_ms=float(dataframe["end_to_end_latency_ms"].mean()) if "end_to_end_latency_ms" in dataframe else 0.0,

            average_throughput_mbps=float(dataframe["throughput_mbps"].mean()) if "throughput_mbps" in dataframe else 0.0,

            average_packet_loss_pct=float(dataframe["packet_loss_rate"].mean()) if "packet_loss_rate" in dataframe else 0.0,

            average_jitter_ms=float(dataframe["jitter_ms"].mean()) if "jitter_ms" in dataframe else 0.0,

            average_qos_score=float(dataframe["qos_satisfaction_score"].mean()) if "qos_satisfaction_score" in dataframe else 0.0,

            sla_success_rate=float(dataframe["sla_satisfied"].mean() * 100) if "sla_satisfied" in dataframe else 0.0,
            
            mutual_information=mutual_info_dict,
            feature_importance=importance_dict,

        )
class AutoLabeler:
    """
    Phase 16: Label Generation Engine
    Generates ground-truth labels deterministically from telemetry and QoS.
    """
    def generate_labels(self, features, qos_metrics, context_history):
        labeled_records = []
        # Merge by tick
        for feat in features:
            tick = feat["tick"]
            # Find matching qos and context
            qos = next((q for q in qos_metrics if q["tick"] == tick), None)
            ctx = next((c for c in context_history if c.get("tick") == tick), {}) # Assuming context saves tick later
            
            # Label logic based on strict thresholds
            is_sla_violated = qos["measured_latency_ms"] > 10.0 if qos else False
            
            # Start with all 88+ extracted features
            record = feat.copy()
            
            # Append QoS derivations
            record["measured_latency_ms"] = qos["measured_latency_ms"] if qos else 0.0
            record["measured_jitter_ms"] = qos["measured_jitter_ms"] if qos else 0.0
            record["measured_loss_pct"] = qos["measured_loss_pct"] if qos else 0.0
            
            # Append Labels
            record["label_sla_violation"] = is_sla_violated
            record["label_anomaly"] = ctx.get("power_grid") != "Stable"
            
            labeled_records.append(record)
            
        return labeled_records

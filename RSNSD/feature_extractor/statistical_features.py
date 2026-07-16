"""
Statistical Feature Extraction

Computes derived statistical features from generated flows.
"""

from statistics import mean
from statistics import median
from statistics import pstdev
from statistics import pvariance


class StatisticalFeatureExtractor:

    def extract(
        self,
        packet_sizes: list[float],
        inter_arrivals: list[float],
    ) -> dict:

        features = {}

        # ----------------------------------------
        # Packet Size Statistics
        # ----------------------------------------

        features["mean_packet_size"] = mean(packet_sizes)

        features["median_packet_size"] = median(packet_sizes)

        features["min_packet_size"] = min(packet_sizes)

        features["max_packet_size"] = max(packet_sizes)

        features["std_packet_size"] = (
            pstdev(packet_sizes)
            if len(packet_sizes) > 1
            else 0
        )

        features["variance_packet_size"] = (
            pvariance(packet_sizes)
            if len(packet_sizes) > 1
            else 0
        )

        # ----------------------------------------
        # IAT Statistics
        # ----------------------------------------

        features["mean_iat_ms"] = mean(inter_arrivals)

        features["min_iat_ms"] = min(inter_arrivals)

        features["max_iat_ms"] = max(inter_arrivals)

        features["std_iat_ms"] = (
            pstdev(inter_arrivals)
            if len(inter_arrivals) > 1
            else 0
        )

        return features
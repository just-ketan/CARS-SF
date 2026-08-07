"""
Base Traffic Behaviour

Defines the abstract interface implemented by every
traffic behaviour model.

Author: RSNSD
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from RSNSD.traffic_generator.common.application_profile import ApplicationProfile
from RSNSD.traffic_generator.common.sampler import Sampler


class BaseBehaviour(ABC):
    """
    Abstract base class for all traffic behaviour models.

    Every behaviour generates realistic traffic characteristics
    for a particular application profile.
    """

    def __init__(self, profile: ApplicationProfile, sampler: Sampler, context=None) -> None:
        self.profile = profile
        self.sampler = sampler
        self.context = context

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Name of the behaviour.
        """
        ...

    def generate_packet_size(self) -> int:
        """
        Generate packet size in bytes.
        """
        return int(self.sampler.sample(self.profile.packet_size_distribution))

    def generate_inter_arrival_time(self) -> float:
        """
        Generate packet inter-arrival time in milliseconds.
        """
        return float(self.sampler.sample(self.profile.inter_arrival_distribution))

    def generate_bitrate(self) -> float:
        """
        Generate instantaneous bitrate in Mbps.
        """
        return max(0.01, float(self.sampler.sample(self.profile.bitrate_distribution)))

    def generate_session_duration(self) -> float:
        """
        Generate session duration in seconds.
        """
        return max(0.01, float(self.sampler.sample(self.profile.session_duration_distribution)))

    @abstractmethod
    def generate_idle_time(self) -> float:
        """
        Generate idle time between sessions in seconds.

        Continuous behaviours may simply return 0.
        """
        ...

    @abstractmethod
    def generate_burst_size(self) -> int:
        """
        Number of packets generated during one burst.

        Continuous behaviours usually return 1.
        """
        ...

    @abstractmethod
    def generate_connection_probability(self) -> float:
        """
        Probability that a user starts a new session
        during the current simulation interval.

        Returns
        -------
        float
            Value in [0, 1].
        """
        ...
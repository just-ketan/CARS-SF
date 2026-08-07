"""
Bursty Traffic Behaviour

Models user-driven bursty traffic such as:

- Social Media
- Instant Messaging
- Push Notifications
- Mobile Apps
- Interactive Dashboards

Author: RSNSD
"""

from __future__ import annotations

import random

from RSNSD.traffic_generator.behaviour.base_behaviour import BaseBehaviour


class BurstyBehaviour(BaseBehaviour):
    """
    Bursty traffic characterized by alternating
    periods of high activity and inactivity.
    """

    @property
    def name(self) -> str:
        return "bursty"

    def generate_idle_time(self) -> float:
        """
        Bursts are separated by idle periods
        caused by user inactivity.
        """

        return round(
            random.uniform(
                2.0,
                20.0,
            ),
            2,
        )

    def generate_burst_size(self) -> int:
        """
        Number of packets generated in one burst.
        """

        return random.randint(
            10,
            100,
        )

    def generate_connection_probability(self) -> float:
        """
        Moderate probability of starting
        a new burst session.
        """

        return 0.60
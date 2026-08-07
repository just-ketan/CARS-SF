"""
Transactional Traffic Behaviour

Models request-response communication.

Typical applications:
- Web Browsing
- Mobile Banking
- E-Governance
- REST APIs
- Database Queries
- Authentication Services

Author: RSNSD
"""

from __future__ import annotations

import random

from RSNSD.traffic_generator.behaviour.base_behaviour import BaseBehaviour


class TransactionalBehaviour(BaseBehaviour):
    """
    Request-response traffic.

    Characteristics
    ---------------
    - Small to medium packets
    - Short-lived sessions
    - Moderate idle periods
    - Multiple independent transactions
    """

    @property
    def name(self) -> str:
        return "transactional"

    def generate_idle_time(self) -> float:
        """
        Idle time between user transactions.
        """

        return round(
            random.uniform(
                1.0,
                10.0,
            ),
            2,
        )

    def generate_burst_size(self) -> int:
        """
        One transaction usually consists of
        several packets.
        """

        return random.randint(
            2,
            10,
        )

    def generate_connection_probability(self) -> float:
        """
        Moderate likelihood of initiating
        a new transaction.
        """

        return 0.75
"""
Traffic Behaviour Factory

Creates the appropriate traffic behaviour model for an
application profile.

Author: RSNSD
"""

from __future__ import annotations

from RSNSD.traffic_generator.behaviour.base_behaviour import BaseBehaviour
from RSNSD.traffic_generator.behaviour.behaviour_type import BehaviourType
from RSNSD.traffic_generator.behaviour.bursty import BurstyBehaviour
from RSNSD.traffic_generator.behaviour.bulk_transfer import BulkTransferBehaviour
from RSNSD.traffic_generator.behaviour.conversational import ConversationalBehaviour
from RSNSD.traffic_generator.behaviour.emergency import EmergencyBehaviour
from RSNSD.traffic_generator.behaviour.periodic import PeriodicBehaviour
from RSNSD.traffic_generator.behaviour.streaming import StreamingBehaviour
from RSNSD.traffic_generator.behaviour.transactional import TransactionalBehaviour
from RSNSD.traffic_generator.common.application_profile import ApplicationProfile
from RSNSD.traffic_generator.common.sampler import Sampler


class BehaviourFactory:
    """
    Factory responsible for constructing traffic
    behaviour models.
    """

    _BEHAVIOURS = {
        BehaviourType.PERIODIC: PeriodicBehaviour,
        BehaviourType.BURSTY: BurstyBehaviour,
        BehaviourType.STREAMING: StreamingBehaviour,
        BehaviourType.CONVERSATIONAL: ConversationalBehaviour,
        BehaviourType.TRANSACTIONAL: TransactionalBehaviour,
        BehaviourType.BULK_TRANSFER: BulkTransferBehaviour,
        BehaviourType.EMERGENCY: EmergencyBehaviour,
    }

    @classmethod
    def create(
        cls,
        profile: ApplicationProfile,
        sampler: Sampler,
        context=None,
    ) -> BaseBehaviour:
        """
        Create a behaviour object for an application profile.

        Parameters
        ----------
        profile : ApplicationProfile

        Returns
        -------
        BaseBehaviour
        """

        behaviour_type = profile.behaviour_type

        behaviour_class = cls._BEHAVIOURS.get(
            behaviour_type
        )

        if behaviour_class is None:
            raise ValueError(
                f"Unsupported behaviour type: {behaviour_type}"
            )

        return behaviour_class(profile, sampler, context)
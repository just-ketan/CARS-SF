"""
Flow Generator

Generates synthetic flow records from application profiles.
"""

from uuid import uuid4

from RSNSD.domain.flow import FlowRecord

from .application_profile import ApplicationProfile
from .sampler import Sampler


class FlowGenerator:

    def __init__(self, sampler: Sampler):

        self.sampler = sampler

    def generate(self, profile: ApplicationProfile, context=None) -> FlowRecord:

        from RSNSD.traffic_generator.behaviour.factory import BehaviourFactory
        behaviour = BehaviourFactory.create(profile, self.sampler, context)

        packet_size = behaviour.generate_packet_size()

        inter_arrival = behaviour.generate_inter_arrival_time()

        duration = behaviour.generate_session_duration()

        bitrate = behaviour.generate_bitrate()

        burst_size = behaviour.generate_burst_size()

        idle_time = behaviour.generate_idle_time()

        return FlowRecord(

            flow_id=str(uuid4()),

            application_id=profile.application_id,

            service_class=profile.service_class.value,

            packet_size=packet_size,

            inter_arrival_time_ms=inter_arrival,

            session_duration_s=duration,

            bitrate_mbps=bitrate,

            burst_size=burst_size,

            idle_time_s=idle_time,

            latency_requirement_ms=profile.latency_requirement_ms,

            jitter_requirement_ms=profile.jitter_requirement_ms,

            packet_loss_requirement_pct=profile.packet_loss_requirement_pct,

            throughput_requirement_mbps=profile.throughput_requirement_mbps,

            metadata=profile.metadata.copy(),
        )
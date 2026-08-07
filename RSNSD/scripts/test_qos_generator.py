from pprint import pprint

from RSNSD.traffic_generator.common.sampler import Sampler
from RSNSD.traffic_generator.common.flow_generator import FlowGenerator
from RSNSD.traffic_generator.common.context_generator import ContextGenerator
from RSNSD.qos import QoSEngine

from RSNSD.traffic_generator.common.scenarios import SCHOOL_HOURS
from RSNSD.traffic_generator.healthcare.telemedicine import TELEMEDICINE


flow = FlowGenerator(
    Sampler(seed=42)
).generate(
    TELEMEDICINE
)

context = ContextGenerator(seed=42).generate(
    TELEMEDICINE,
    SCHOOL_HOURS,
)

qos = QoSEngine().compute(
    flow,
    context,
)

pprint(qos)
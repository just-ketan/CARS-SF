from pprint import pprint

from RSNSD.traffic_generator.common.flow_generator import FlowGenerator
from RSNSD.traffic_generator.common.sampler import Sampler

from RSNSD.traffic_generator.healthcare.telemedicine import TELEMEDICINE


generator = FlowGenerator(Sampler(seed=42))

flow = generator.generate(TELEMEDICINE)

pprint(flow)
from pprint import pprint

from RSNSD.traffic_generator.common.context_generator import ContextGenerator
from RSNSD.traffic_generator.common.scenarios import SCHOOL_HOURS
from RSNSD.traffic_generator.healthcare.telemedicine import TELEMEDICINE

generator = ContextGenerator(seed=42)

context = generator.generate(
    TELEMEDICINE,
    SCHOOL_HOURS,
)

pprint(context)
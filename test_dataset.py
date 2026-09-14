import sys
sys.path.insert(0, "/home/ketan/Desktop/Projects/CARS-SF")
from RSNSD.traffic_generator.common.dataset_builder import DatasetBuilder
from RSNSD.traffic_generator.common.flow_generator import FlowGenerator
from RSNSD.traffic_generator.common.context_generator import ContextGenerator
from RSNSD.traffic_generator.common.scenarios import NORMAL
from RSNSD.traffic_generator.healthcare.remote_surgery import REMOTE_SURGERY
from RSNSD.traffic_generator.common.sampler import Sampler

sampler = Sampler(42)
fg = FlowGenerator(sampler)
cg = ContextGenerator(42)
db = DatasetBuilder(fg, cg, 42)

records = db.generate_dataset([REMOTE_SURGERY], NORMAL, 10, [1.0])
for r in records:
    print(r.context.time_of_day, r.context.active_users, r.context.network_load_pct)

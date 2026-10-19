"""Traffic models: mean-rate conformance, burst structure, demand scaling."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from traffic.models import mean_rate_mbps, scaled, schedule


def _rate(events, duration):
    return sum(size for _, _, size in events) * 8 / duration / 1e6


@pytest.mark.parametrize("model,params,tolerance", [
    ("cbr", {"rate_mbps": 5.0}, 0.02),
    ("vbr_video", {"rate_mbps": 8.0, "fps": 25, "gop": 25}, 0.08),
    ("onoff", {"rate_mbps": 2.0, "mean_on_s": 0.5, "mean_off_s": 0.5}, 0.35),
    ("iot_periodic", {"period_s": 0.1, "size": 500}, 0.05),
    ("voip", {}, 0.35),
])
def test_long_run_rate_matches_nominal(model, params, tolerance):
    duration = 120.0
    events = schedule(model, params, duration, seed=1)
    nominal = mean_rate_mbps(model, params)
    assert abs(_rate(events, duration) - nominal) / nominal < tolerance


def test_events_are_time_ordered_and_within_duration():
    events = schedule("vbr_video", {"rate_mbps": 4.0}, 10.0, seed=3, instances=2)
    times = [t for t, _, _ in events]
    assert times == sorted(times)
    assert 0 <= times[0] and times[-1] < 10.0
    assert {i for _, i, _ in events} == {0, 1}
    assert max(size for _, _, size in events) <= 1200


def test_video_has_i_frame_bursts():
    events = schedule("vbr_video", {"rate_mbps": 8.0, "fps": 25, "gop": 25, "cv": 0.0}, 2.0, seed=0)
    per_frame = {}
    for t, _, size in events:
        per_frame.setdefault(round(t, 2), 0)
        per_frame[round(t, 2)] += size
    sizes = np.array(list(per_frame.values()))
    assert sizes.max() > 3 * np.median(sizes)


def test_scaling_rate_models_and_fixed_devices():
    params, instances = scaled("vbr_video", {"rate_mbps": 4.0}, 2.5)
    assert params["rate_mbps"] == 10.0 and instances == 1
    params, instances = scaled("iot_periodic", {"period_s": 1.0}, 3.4)
    assert params == {"period_s": 1.0} and instances == 3


def test_seeded_schedules_are_reproducible():
    a = schedule("onoff", {"rate_mbps": 1.0}, 20.0, seed=11)
    b = schedule("onoff", {"rate_mbps": 1.0}, 20.0, seed=11)
    assert a == b


def test_generator_paces_without_busy_waiting():
    import time as _time

    from traffic.generator import _sleep_until

    start_cpu, start_wall = _time.process_time(), _time.perf_counter()
    for i in range(200):                       # 200 deadlines 0.25 ms apart (≈ 4000 pps)
        _sleep_until(start_wall + i * 0.00025)
    cpu = _time.process_time() - start_cpu
    assert cpu < 0.02, f"pacing burned {cpu:.3f}s of CPU"

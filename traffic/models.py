"""
Application traffic models.

Each packet model is a generator of ``(t_offset_s, payload_bytes)`` send events
for one flow. They are pure (seeded RNG, no I/O) so they can be unit-tested and
reused by the live generator. Rates are mean application rates in Mbps.

Models (and the rural applications they stand for):
  cbr           constant bit rate                      (baseline / legacy)
  vbr_video     GOP-structured variable-bit-rate video (telemedicine, classroom, drones)
  voip          on/off talkspurts, 50 pps              (emergency voice)
  iot_periodic  periodic small reports with jitter     (ECG, soil, weather sensors)
  onoff         Pareto on/off bursts                   (ambulance telemetry, irrigation)

TCP models (bulk_tcp, web_tcp, chunked_tcp) are byte-stream driven and are
implemented in ``traffic/generator.py`` using the helpers below.
"""

from __future__ import annotations

import math
from typing import Iterator

import numpy as np

MAX_PAYLOAD = 1200          # bytes per datagram (stays below the 1500 B MTU)
UDP_HEADER_BYTES = 18       # magic(2) + seq(8) + send timestamp(8), see generator


def _bytes_per_s(rate_mbps: float) -> float:
    return rate_mbps * 1_000_000 / 8


def cbr(rng, duration: float, rate_mbps: float, size: int = MAX_PAYLOAD) -> Iterator[tuple[float, int]]:
    interval = size / _bytes_per_s(rate_mbps)
    t = rng.uniform(0, interval)
    while t < duration:
        yield t, size
        t += interval


def vbr_video(
    rng,
    duration: float,
    rate_mbps: float,
    fps: int = 25,
    gop: int = 25,
    i_ratio: float = 4.0,
    cv: float = 0.25,
) -> Iterator[tuple[float, int]]:
    """I-frame every ``gop`` frames, ``i_ratio`` × a P-frame; lognormal frame-size noise."""
    mean_frame = _bytes_per_s(rate_mbps) / fps
    p_size = mean_frame * gop / (i_ratio + gop - 1)
    sigma = math.sqrt(math.log(1 + cv ** 2))
    frame_interval = 1.0 / fps
    t, frame = rng.uniform(0, frame_interval), 0
    while t < duration:
        base = p_size * (i_ratio if frame % gop == 0 else 1.0)
        size = int(base * rng.lognormal(-sigma ** 2 / 2, sigma))
        # A frame leaves as a back-to-back burst spread over ~1 ms.
        n_packets = max(1, math.ceil(size / MAX_PAYLOAD))
        for k in range(n_packets):
            chunk = min(MAX_PAYLOAD, size - k * MAX_PAYLOAD) if size > 0 else 64
            yield t + k * (0.001 / n_packets), max(chunk, 64)
        t += frame_interval
        frame += 1


def voip(
    rng,
    duration: float,
    mean_on_s: float = 1.0,
    mean_off_s: float = 1.35,
    pps: int = 50,
    size: int = 172,
) -> Iterator[tuple[float, int]]:
    """G.711-like: 160 B voice + RTP header every 20 ms during exponential talkspurts."""
    t = rng.exponential(mean_off_s)
    while t < duration:
        end = t + rng.exponential(mean_on_s)
        while t < min(end, duration):
            yield t, size
            t += 1.0 / pps
        t = end + rng.exponential(mean_off_s)


def iot_periodic(
    rng,
    duration: float,
    period_s: float = 1.0,
    size: int = 200,
    jitter: float = 0.1,
) -> Iterator[tuple[float, int]]:
    t = rng.uniform(0, period_s)
    while t < duration:
        yield t, size
        t += period_s * (1 + rng.uniform(-jitter, jitter))


def onoff(
    rng,
    duration: float,
    rate_mbps: float,
    mean_on_s: float = 0.5,
    mean_off_s: float = 1.0,
    shape: float = 1.5,
    size: int = 1000,
) -> Iterator[tuple[float, int]]:
    """Heavy-tailed (Pareto) on/off source whose long-run mean is ``rate_mbps``."""
    duty = mean_on_s / (mean_on_s + mean_off_s)
    interval = size / (_bytes_per_s(rate_mbps) / duty)

    def pareto(mean: float) -> float:
        scale = mean * (shape - 1) / shape
        return scale * (1 + rng.pareto(shape))

    t = rng.uniform(0, mean_off_s)
    while t < duration:
        end = t + pareto(mean_on_s)
        while t < min(end, duration):
            yield t, size
            t += interval
        t = end + pareto(mean_off_s)


PACKET_MODELS = {
    "cbr": cbr,
    "vbr_video": vbr_video,
    "voip": voip,
    "iot_periodic": iot_periodic,
    "onoff": onoff,
}
TCP_MODELS = {"bulk_tcp", "web_tcp", "chunked_tcp"}
# Models whose load is fixed per device: demand scaling adds devices instead of rate.
FIXED_RATE_MODELS = {"voip", "iot_periodic"}


def pareto_size(rng, mean: float, shape: float = 1.3, cap_factor: float = 50.0) -> int:
    scale = mean * (shape - 1) / shape
    return int(min(scale * (1 + rng.pareto(shape)), mean * cap_factor))


def mean_rate_mbps(model: str, params: dict) -> float:
    """Long-run mean application rate of a model instance (for demand scaling)."""
    if "rate_mbps" in params:
        return float(params["rate_mbps"])
    if model == "voip":
        on, off = params.get("mean_on_s", 1.0), params.get("mean_off_s", 1.35)
        return params.get("pps", 50) * params.get("size", 172) * 8 / 1e6 * on / (on + off)
    if model == "iot_periodic":
        return params.get("size", 200) * 8 / params.get("period_s", 1.0) / 1e6
    return 0.0


def scaled(model: str, params: dict, scale: float) -> tuple[dict, int]:
    """Apply a demand scale factor: returns (params, instances)."""
    params = dict(params)
    if model in FIXED_RATE_MODELS:
        return params, int(min(max(round(scale), 1), 50))
    if "rate_mbps" in params:
        params["rate_mbps"] = max(round(params["rate_mbps"] * scale, 4), 0.01)
    return params, 1


def schedule(model: str, params: dict, duration: float, seed: int, instances: int = 1):
    """Merged, time-sorted send events ``(t, instance, size)`` for packet models."""
    fn = PACKET_MODELS[model]
    events = []
    for i in range(instances):
        rng = np.random.default_rng(seed + 7919 * i)
        events.extend((t, i, size) for t, size in fn(rng, duration, **params))
    events.sort()
    return events

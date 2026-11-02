"""
Direction model of the full-duplex rural uplink.

The link carries 100 Mb/s in *each* direction and HTB enforces each direction
separately (uplink egress on s_rural, downlink egress on s_edge). A slice's
demand therefore has to be compared with the capacity of the direction it
actually loads: healthcare and agriculture are uplink services (telemedicine,
ambulance video, sensors), education and general are downlink services. Adding
both directions together and comparing with one direction's capacity misjudges
contention, e.g. in a disaster healthcare's 90 Mb/s fits the 100 Mb/s uplink
even though the total offered load (120 Mb/s) exceeds 100.

The split comes from the application registry: the share of each service's
nominal rate whose data direction is "up". Reverse traffic (TCP ACKs, requests)
is small and is covered by the per-direction floors.
"""

from __future__ import annotations

from functools import lru_cache

from core.config import load_applications

UPLINK, DOWNLINK = "uplink", "downlink"
DIRECTIONS = (UPLINK, DOWNLINK)
SERVICES = ("healthcare", "education", "agriculture", "general")


def _nominal_rate(app: dict) -> float:
    params = app.get("params") or {}
    if "rate_mbps" in params:
        return float(params["rate_mbps"])
    if "pps" in params and "size" in params:
        return params["pps"] * params["size"] * 8 / 1e6
    if "period_s" in params:
        return params.get("size", 200) * 8 / params["period_s"] / 1e6
    return 0.1


@lru_cache(maxsize=1)
def uplink_share() -> dict[str, float]:
    """Fraction of each service's nominal offered rate that flows uplink."""
    up = {s: 0.0 for s in SERVICES}
    total = {s: 0.0 for s in SERVICES}
    for app in load_applications():
        service = app["service_class"]
        if service not in total:
            continue
        rate = _nominal_rate(app)
        total[service] += rate
        if app.get("direction", "up") == "up":
            up[service] += rate
    return {s: (up[s] / total[s] if total[s] else 0.5) for s in SERVICES}


@lru_cache(maxsize=1)
def elastic_directions() -> dict[str, set[str]]:
    """Directions in which a service carries elastic (TCP) data traffic.

    Only TCP adapts its rate to the allocation, so only there is the true demand
    unobservable and worth probing for; UDP offered load is measured directly.
    """
    out: dict[str, set[str]] = {s: set() for s in SERVICES}
    for app in load_applications():
        if app.get("protocol") == "tcp" and app["service_class"] in out:
            out[app["service_class"]].add(UPLINK if app.get("direction", "up") == "up" else DOWNLINK)
    return out


def split_demand(total: dict[str, float]) -> dict[str, dict[str, float]]:
    """Total (both-direction) demand → per-direction demand."""
    share = uplink_share()
    return {
        UPLINK: {s: total.get(s, 0.0) * share[s] for s in total},
        DOWNLINK: {s: total.get(s, 0.0) * (1 - share[s]) for s in total},
    }


def dominant_direction(service: str) -> str:
    return UPLINK if uplink_share().get(service, 0.5) >= 0.5 else DOWNLINK


def flatten(directional: dict[str, dict[str, float]]) -> dict[str, float]:
    """One number per slice for logs and the RL state: its rate in its dominant direction."""
    return {s: directional[dominant_direction(s)].get(s, 0.0) for s in directional[UPLINK]}

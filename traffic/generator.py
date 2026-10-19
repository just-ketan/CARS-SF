"""
Traffic generator process, launched on a Mininet host by TrafficOrchestrator.

    python -m traffic.generator --proto udp --dst 10.0.2.10 --port 5001 \
        --model vbr_video --params '{"rate_mbps": 5}' --duration 30 --dscp 46

UDP payloads start with a header (magic, sequence number, send timestamp) so
every datagram is unique and can be matched across capture points. DSCP is set
on the socket (IP_TOS) the way a slice-aware application would mark traffic.
"""

from __future__ import annotations

import argparse
import json
import socket
import struct
import time

import numpy as np

from traffic.models import MAX_PAYLOAD, PACKET_MODELS, pareto_size, schedule

UDP_MAGIC = b"CS"
RR_MAGIC = b"RR"
RR_HEADER = struct.Struct("!2sIH")   # magic, response bytes, request padding bytes


# Packets due within this horizon are sent back-to-back instead of sleeping.
# Never busy-wait: dozens of generators share the host with the emulated
# network, and spinning processes starve the kernel's netem/HTB timers.
BATCH_HORIZON_S = 0.0005


def _sleep_until(deadline: float):
    remaining = deadline - time.perf_counter()
    if remaining > BATCH_HORIZON_S:
        time.sleep(remaining)


def _socket(kind: int, dscp: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, kind)
    if dscp:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, dscp << 2)
    return sock


def run_udp(args, params: dict):
    events = schedule(args.model, params, args.duration, args.seed, args.instances)
    socks = [_socket(socket.SOCK_DGRAM, args.dscp) for _ in range(args.instances)]
    padding = bytes(MAX_PAYLOAD)
    seq = 0
    start = time.perf_counter()
    for t, instance, size in events:
        _sleep_until(start + t)
        header = UDP_MAGIC + struct.pack("!Qd", seq, time.time())
        try:
            socks[instance].sendto(header + padding[: max(size - len(header), 0)], (args.dst, args.port))
        except OSError:
            pass  # e.g. ENETUNREACH during a link failure; keep the schedule
        seq += 1


def _connect(args) -> socket.socket:
    deadline = time.time() + 10
    while True:
        sock = _socket(socket.SOCK_STREAM, args.dscp)
        try:
            sock.connect((args.dst, args.port))
            return sock
        except OSError:
            sock.close()
            if time.time() > deadline:
                raise
            time.sleep(0.2)


def run_bulk_tcp(args, params: dict, end: float):
    """Token-bucket paced bulk transfer (TCP backpressure applies when congested)."""
    rate = params.get("rate_mbps", 10) * 1e6 / 8
    sock = _connect(args)
    chunk = bytes(16384)
    sent, start = 0, time.perf_counter()
    while time.time() < end:
        allowed = rate * (time.perf_counter() - start)
        if sent + len(chunk) > allowed:
            _sleep_until(start + (sent + len(chunk)) / rate)
            continue
        sock.sendall(chunk)
        sent += len(chunk)
    sock.close()


def _request(sock: socket.socket, response_bytes: int, request_bytes: int):
    sock.sendall(RR_HEADER.pack(RR_MAGIC, response_bytes, request_bytes) + bytes(request_bytes))
    remaining = response_bytes
    while remaining > 0:
        data = sock.recv(min(remaining, 65536))
        if not data:
            raise ConnectionError("server closed")
        remaining -= len(data)


def run_web_tcp(args, params: dict, end: float, rng):
    """Persistent connection, Pareto response sizes, exponential think time."""
    rate = params.get("rate_mbps", 1) * 1e6 / 8
    mean_resp = params.get("mean_response_kb", 200) * 1000
    request_bytes = params.get("request_bytes", 400)
    sock = _connect(args)
    while time.time() < end:
        size = max(pareto_size(rng, mean_resp), 1000)
        started = time.time()
        _request(sock, size, request_bytes)
        think = rng.exponential(mean_resp / rate)
        time.sleep(max(0.0, min(think - (time.time() - started), end - time.time())))
    sock.close()


def run_chunked_tcp(args, params: dict, end: float):
    """DASH-like: one segment of ``rate × chunk_s`` bytes every ``chunk_s`` seconds."""
    rate = params.get("rate_mbps", 5) * 1e6 / 8
    chunk_s = params.get("chunk_s", 2.0)
    sock = _connect(args)
    next_request = time.time()
    while time.time() < end:
        _request(sock, int(rate * chunk_s), params.get("request_bytes", 300))
        next_request += chunk_s
        time.sleep(max(0.0, min(next_request - time.time(), end - time.time())))
    sock.close()


def main():
    parser = argparse.ArgumentParser(description="CARS-SF application traffic generator")
    parser.add_argument("--proto", choices=["udp", "tcp"], required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--params", default="{}")
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--dscp", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--instances", type=int, default=1)
    args = parser.parse_args()
    params = json.loads(args.params)
    end = time.time() + args.duration
    rng = np.random.default_rng(args.seed)

    try:
        if args.model in PACKET_MODELS:
            run_udp(args, params)
        elif args.model == "bulk_tcp":
            run_bulk_tcp(args, params, end)
        elif args.model == "web_tcp":
            run_web_tcp(args, params, end, rng)
        elif args.model == "chunked_tcp":
            run_chunked_tcp(args, params, end)
        else:
            raise SystemExit(f"unknown model {args.model}")
    except (ConnectionError, OSError) as exc:
        print(f"generator stopped: {exc}", flush=True)


if __name__ == "__main__":
    main()

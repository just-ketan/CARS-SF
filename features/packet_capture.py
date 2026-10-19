"""
Endpoint packet captures → matched per-packet observations.

Every UE and server interface is captured (tcpdump, 128 B snap length). A
packet therefore appears twice: as *tx* in its sender's capture and as *rx* in
its receiver's capture. All hosts share one clock (Mininet namespaces on one
kernel), so ``rx_ts - tx_ts`` is the true one-way delay, a tx without an rx is
a lost packet, and a repeated TCP segment at the sender is a retransmission.

Packets are matched on a fingerprint that is unique in practice: addresses,
ports, IP ID, TCP seq/ack and the first payload bytes (the generator puts a
sequence number and timestamp at the start of every UDP payload).
"""

from __future__ import annotations

import socket
from collections import defaultdict, deque
from dataclasses import dataclass

import dpkt
import pandas as pd

# Packets sent this close to the end of capture may still be in flight.
IN_FLIGHT_GUARD_S = 1.0


@dataclass(frozen=True)
class CapturePoint:
    path: str
    host_ip: str


def _ip_str(raw: bytes) -> str:
    return socket.inet_ntoa(raw)


def _link_decoder(datalink: int):
    """Frame → IP packet for the capture's link type (Ethernet, raw IP, Linux SLL)."""
    if datalink in (dpkt.pcap.DLT_RAW, 12, 14, 101, 228):     # raw IP (LINKTYPE_RAW = 101; TUN devices)
        return lambda buf: dpkt.ip.IP(buf)
    if datalink == dpkt.pcap.DLT_LINUX_SLL:
        return lambda buf: dpkt.sll.SLL(buf).data
    return lambda buf: dpkt.ethernet.Ethernet(buf).data


def parse_capture(point: CapturePoint) -> list[tuple]:
    """Return (ts, direction, fingerprint, fields) for IPv4 packets of one capture."""
    rows = []
    try:
        handle = open(point.path, "rb")
    except OSError:
        return rows
    with handle:
        try:
            reader = dpkt.pcap.Reader(handle)
        except (ValueError, dpkt.dpkt.NeedData):
            return rows
        decode = _link_decoder(reader.datalink())
        try:
            for ts, buf in reader:
                try:
                    ip = decode(buf)
                except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
                    continue
                if not isinstance(ip, dpkt.ip.IP):
                    continue
                src, dst = _ip_str(ip.src), _ip_str(ip.dst)
                if src == point.host_ip:
                    direction = "tx"
                elif dst == point.host_ip:
                    direction = "rx"
                else:
                    continue
                sport = dport = seq = ack = win = flags = 0
                payload_len, head = 0, b""
                l4 = ip.data
                if isinstance(l4, dpkt.tcp.TCP):
                    sport, dport, seq, ack = l4.sport, l4.dport, l4.seq, l4.ack
                    win, flags = l4.win, l4.flags
                    payload_len = ip.len - ip.hl * 4 - l4.off * 4
                    head = bytes(l4.data[:16])
                elif isinstance(l4, dpkt.udp.UDP):
                    sport, dport = l4.sport, l4.dport
                    payload_len = l4.ulen - 8
                    head = bytes(l4.data[:18])
                elif isinstance(l4, dpkt.icmp.ICMP):
                    head = bytes(l4.data)[:8]
                    payload_len = ip.len - ip.hl * 4 - 8
                else:
                    continue
                fingerprint = (src, dst, ip.p, sport, dport, ip.id, seq, ack, payload_len, head)
                rows.append((
                    float(ts), direction, fingerprint,
                    (src, dst, ip.p, sport, dport, ip.len, ip.ttl, ip.tos >> 2,
                     flags, win, seq, payload_len),
                ))
        except (dpkt.dpkt.NeedData, ValueError):
            pass  # truncated final record of a capture that was still being written
    return rows


def match_packets(points: list[CapturePoint], ue_ips: set[str]) -> pd.DataFrame:
    """One row per transmitted packet with its receive time (NaN if lost)."""
    tx_rows, rx_by_fp = [], defaultdict(deque)
    capture_end = None
    for point in points:
        rows = parse_capture(point)
        if rows:
            end = max(r[0] for r in rows)
            capture_end = end if capture_end is None else min(capture_end, end)
        for ts, direction, fp, fields in rows:
            if direction == "tx":
                tx_rows.append((ts, fp, fields))
            else:
                rx_by_fp[fp].append(ts)

    columns = [
        "tx_ts", "rx_ts", "flow", "direction", "src", "dst", "proto", "sport", "dport",
        "ip_len", "ttl", "dscp", "tcp_flags", "tcp_win", "tcp_seq", "payload_len",
        "retransmission", "in_flight",
    ]
    if not tx_rows:
        return pd.DataFrame(columns=columns)

    tx_rows.sort(key=lambda r: r[0])
    for queue in rx_by_fp.values():
        queue_sorted = sorted(queue)
        queue.clear()
        queue.extend(queue_sorted)

    seen_segments: set = set()
    out = []
    for ts, fp, fields in tx_rows:
        src, dst, proto, sport, dport, ip_len, ttl, dscp, flags, win, seq, payload_len = fields
        if src in ue_ips:
            flow, direction = (src, dst, proto, sport, dport), 1
        elif dst in ue_ips:
            flow, direction = (dst, src, proto, dport, sport), -1
        else:
            continue
        rx_ts = float("nan")
        queue = rx_by_fp.get(fp)
        while queue and queue[0] < ts - 1e-6:
            queue.popleft()  # stale receive of an earlier identical packet
        if queue:
            rx_ts = queue.popleft()
        retrans = False
        if proto == 6 and payload_len > 0:
            key = (flow, direction, seq, payload_len)
            retrans = key in seen_segments
            seen_segments.add(key)
        out.append((
            ts, rx_ts, flow, direction, src, dst, proto, sport, dport, ip_len, ttl, dscp,
            flags, win, seq, payload_len, retrans,
            capture_end is not None and ts > capture_end - IN_FLIGHT_GUARD_S,
        ))
    df = pd.DataFrame(out, columns=columns)
    df["owd_ms"] = (df["rx_ts"] - df["tx_ts"]) * 1000.0
    return df

"""
Traffic sink process: receives UDP datagrams and TCP streams on a set of ports.

TCP connections that open with the request/response header from
``traffic.generator`` (web_tcp / chunked_tcp) get a response of the requested
size; anything else is read and discarded (bulk uploads).

    python -m traffic.sink --udp 5001,5003 --tcp 5004,5005
"""

from __future__ import annotations

import argparse
import socket
import threading

from traffic.generator import RR_HEADER, RR_MAGIC

_ZEROS = bytes(65536)


def _recv_exact(conn: socket.socket, n: int) -> bytes | None:
    buf = bytearray()
    while len(buf) < n:
        data = conn.recv(n - len(buf))
        if not data:
            return None
        buf.extend(data)
    return bytes(buf)


def _serve_tcp(conn: socket.socket):
    try:
        first = _recv_exact(conn, RR_HEADER.size)
        if first is None:
            return
        magic, response_bytes, request_bytes = RR_HEADER.unpack(first)
        if magic != RR_MAGIC:
            while conn.recv(65536):
                pass
            return
        while True:
            if _recv_exact(conn, request_bytes) is None:
                return
            remaining = response_bytes
            while remaining > 0:
                n = min(remaining, len(_ZEROS))
                conn.sendall(_ZEROS[:n])
                remaining -= n
            header = _recv_exact(conn, RR_HEADER.size)
            if header is None:
                return
            _, response_bytes, request_bytes = RR_HEADER.unpack(header)
    except OSError:
        pass
    finally:
        conn.close()


def _tcp_listener(port: int):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(64)
    while True:
        conn, _ = server.accept()
        threading.Thread(target=_serve_tcp, args=(conn,), daemon=True).start()


def _udp_listener(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)
    sock.bind(("0.0.0.0", port))
    while True:
        sock.recv(65536)


def _ports(raw: str) -> list[int]:
    return [int(p) for p in raw.split(",") if p]


def main():
    parser = argparse.ArgumentParser(description="CARS-SF traffic sink")
    parser.add_argument("--udp", default="")
    parser.add_argument("--tcp", default="")
    args = parser.parse_args()
    threads = [
        threading.Thread(target=_udp_listener, args=(p,), daemon=True) for p in _ports(args.udp)
    ] + [
        threading.Thread(target=_tcp_listener, args=(p,), daemon=True) for p in _ports(args.tcp)
    ]
    for thread in threads:
        thread.start()
    print("sink ready", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()

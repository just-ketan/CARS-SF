#!/bin/bash
# All Open5GS 5GC network functions in one container (SBI on loopback).
set -e
if ! grep -q ogstun /proc/net/dev; then ip tuntap add name ogstun mode tun; fi
for gw in 10.60.0.1/24 10.61.0.1/24 10.62.0.1/24 10.63.0.1/24; do
  ip addr add "$gw" dev ogstun 2>/dev/null || true
done
ip link set ogstun up
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true   # also set via compose sysctls
# Loopback aliases used by the SBI/PFCP servers.
for i in 4 5 7 10 11 12 13 14 15 20 200; do ip addr add 127.0.0.$i/8 dev lo 2>/dev/null || true; done
# UDR and PCF need the subscriber database: wait until MongoDB accepts connections.
for _ in $(seq 60); do (exec 3<>/dev/tcp/mongo/27017) 2>/dev/null && break; sleep 1; done
cd /opt/open5gs
for nf in nrf scp; do bin/open5gs-${nf}d -c /config/${nf}.yaml & sleep 1; done
sleep 2
for nf in ausf udm udr pcf nssf bsf; do bin/open5gs-${nf}d -c /config/${nf}.yaml & done
sleep 2
bin/open5gs-upfd -c /config/upf.yaml &
sleep 1
bin/open5gs-smfd -c /config/smf.yaml &
sleep 1
bin/open5gs-amfd -c /config/amf.yaml &
echo "CARS-SF 5GC started"
wait -n

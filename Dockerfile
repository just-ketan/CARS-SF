# CARS-SF reproducible environment: Mininet + Open vSwitch + the full pipeline.
#
#   docker build -t cars-sf .
#   docker run --rm -it --privileged -v /lib/modules:/lib/modules:ro cars-sf \
#       make regression
#   docker run --rm -it --privileged -v /lib/modules:/lib/modules:ro cars-sf \
#       .venv/bin/python run_experiment.py --scenario fiber_cut --duration 45 --apply-qos
#
# --privileged is required: Mininet creates network namespaces, veth pairs and
# qdiscs, and Open vSwitch needs its kernel datapath module from the host.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        mininet openvswitch-switch openvswitch-common iproute2 iputils-ping \
        tcpdump bridge-utils ethtool python3 python3-venv python3-pip make git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /cars-sf
COPY requirements.txt .
RUN python3 -m venv --system-site-packages .venv \
    && .venv/bin/python -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && .venv/bin/python -m pip install --no-cache-dir -r requirements.txt
COPY . .

# Start Open vSwitch before any command (OVSBridge needs ovsdb-server/ovs-vswitchd).
RUN printf '#!/bin/sh\n/usr/share/openvswitch/scripts/ovs-ctl start --system-id=random >/dev/null 2>&1\nexec "$@"\n' \
        > /usr/local/bin/with-ovs && chmod +x /usr/local/bin/with-ovs
ENTRYPOINT ["/usr/local/bin/with-ovs"]
CMD ["make", "test"]

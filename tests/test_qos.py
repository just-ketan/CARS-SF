"""QoS enforcer command generation (no network needed)."""

from slicing.qos_enforcer import QoSEnforcer


class FakeSwitch:
    def __init__(self, name):
        self.name, self.commands = name, []

    def cmd(self, command):
        self.commands.append(command)


class FakeNet:
    def __init__(self):
        self.switches = {n: FakeSwitch(n) for n in ("s_rural", "s_edge")}

    def get(self, name):
        return self.switches[name]


SPAWN = {"host_ip": "10.0.1.10", "server_ip": "10.0.2.10", "port": 5001,
         "service_class": "healthcare", "slice_type": "URLLC", "protocol": "udp"}


def test_service_classes_on_both_directions_with_fq_codel_and_host_filters():
    net = FakeNet()
    qos = QoSEnforcer(net=net)
    qos.setup_htb(100, spawns=[SPAWN])
    for name, iface in (("s_rural", "s_rural-up"), ("s_edge", "s_edge-down")):
        cmds = "\n".join(net.switches[name].commands)
        assert f"dev {iface} root handle 1: htb default 40" in cmds
        assert cmds.count("fq_codel") == 4
    up = "\n".join(net.switches["s_rural"].commands)
    down = "\n".join(net.switches["s_edge"].commands)
    assert "match ip src 10.0.1.10/32 flowid 1:10" in up
    assert "match ip dst 10.0.1.10/32 flowid 1:10" in down


def test_work_conserving_vs_strict_caps():
    for wc, ceil in ((True, "ceil 100mbit"), (False, "ceil 30mbit")):
        net = FakeNet()
        qos = QoSEnforcer(net=net, work_conserving=wc)
        qos.setup_htb(100)
        qos.apply_allocation({"healthcare": 30})
        changes = [c for c in net.switches["s_rural"].commands if c.startswith("tc class change")]
        assert f"classid 1:10 htb rate 30mbit {ceil}" in changes[-1]


def test_tgpp_mode_maps_applications_by_slice_type():
    net = FakeNet()
    qos = QoSEnforcer(net=net, class_mode="tgpp")
    qos.setup_htb(100, spawns=[SPAWN])
    cmds = "\n".join(net.switches["s_rural"].commands)
    assert "htb default 20" in cmds          # eMBB is the default slice
    assert "match ip dport 5001 0xffff flowid 1:10" in cmds


def test_no_slicing_is_single_fifo():
    net = FakeNet()
    qos = QoSEnforcer(net=net, class_mode="none")
    qos.setup_htb(100)
    cmds = "\n".join(net.switches["s_rural"].commands)
    assert "pfifo limit 1000" in cmds and "fq_codel" not in cmds


def test_flow_rules_are_installed_once():
    net = FakeNet()
    qos = QoSEnforcer(net=net, classification="slicenet")
    qos.setup_htb(100)
    flow = ("10.0.1.60", "10.0.3.10", 17, 40000, 5001)
    assert qos.classify_flow(flow, "education") is True
    assert qos.classify_flow(flow, "general") is False
    assert "match ip sport 40000 0xffff match ip dport 5001 0xffff flowid 1:20" in net.switches["s_rural"].commands[-1]


class KernelSwitch(FakeSwitch):
    """Fake switch that answers exit codes and `tc class show` like the kernel."""

    def __init__(self, name, fail_on=None, drift=0):
        super().__init__(name)
        self.classes, self.fail_on, self.drift = {}, fail_on, drift

    def cmd(self, command):
        self.commands.append(command)
        import re
        if command.startswith("tc class show"):
            return "\n".join(f"class htb {c} parent 1:1 prio 1 rate {r}Mbit ceil {ce}Mbit burst 1600b"
                             for c, (r, ce) in self.classes.items())
        m = re.search(r"classid (\d+:\d+) htb rate (\d+)mbit ceil (\d+)mbit", command)
        failed = self.fail_on and self.fail_on in command
        if m and not failed:
            self.classes[m.group(1)] = (int(m.group(2)) + self.drift, int(m.group(3)))
        return f"__rc={1 if failed else 0}" if "__rc" in command else ""


class KernelNet(FakeNet):
    def __init__(self, **kw):
        self.switches = {n: KernelSwitch(n, **kw) for n in ("s_rural", "s_edge")}


def test_enforcement_is_verified_by_kernel_readback():
    qos = QoSEnforcer(net=KernelNet())
    qos.setup_htb(100)
    result = qos.apply_allocation({"healthcare": 30, "education": 40, "agriculture": 10, "general": 20})
    assert result["verified"] is True and not result["failures"] and not result["mismatches"]


def test_failed_command_and_kernel_drift_are_reported():
    qos = QoSEnforcer(net=KernelNet(fail_on="classid 1:20"))
    qos.setup_htb(100)
    result = qos.apply_allocation({"healthcare": 30, "education": 40})
    assert result["verified"] is False and {f["class"] for f in result["failures"]} == {"education"}

    drifted = QoSEnforcer(net=KernelNet(drift=7))
    drifted.setup_htb(100)
    result = drifted.apply_allocation({"healthcare": 30})
    assert result["verified"] is False and result["mismatches"][0]["actual"][0] == 37


def test_controller_keeps_last_good_allocation_when_enforcement_fails():
    from core.controller import SliceController

    class FailingQoS:
        def apply_allocation(self, allocation, ceilings=None):
            return {"verified": False, "failures": [{"class": "x", "rc": 2}], "mismatches": []}

    ctl = SliceController("proposed", 100, qos=FailingQoS(), control_interval_ticks=1)
    start = ctl.start("school", {"healthcare": 5, "education": 80, "agriculture": 10, "general": 50})
    snap = {"interval_s": 1.0, "service_throughput_mbps": {"healthcare": 30, "education": 1, "agriculture": 1, "general": 1}}
    for t in range(1, 4):
        assert ctl.step(t, snap, {"context": "disaster"}, {"state": "normal", "boosts": {}},
                        {"healthcare": 90, "education": 5, "agriculture": 5, "general": 20}) is None
    assert ctl.allocation == start and ctl.enforcement_failures >= 1
    assert ctl.history[-1]["enforcement"]["verified"] is False

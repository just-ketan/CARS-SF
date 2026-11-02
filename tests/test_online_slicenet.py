"""Module E: SliceNet as the default classifier — incremental capture reading, early
decisions, confidence fallback and confirmed reclassification."""

import struct
from collections import deque

import pytest

from classification import online
from classification.slicenet import FALLBACK_CLASS
from features.packet_capture import CapturePoint, IncrementalCaptureReader

FLOW = ("10.0.1.10", "10.0.2.10", 17, 40000, 5001)


class FakeQos:
    def __init__(self):
        self.flow_rules, self.calls = {}, []

    def classify_flow(self, flow, cls, replace=False):
        if flow in self.flow_rules and not replace:
            return False
        self.flow_rules[flow] = cls
        self.calls.append((flow, cls, replace))
        return True


class ScriptedModel:
    def __init__(self, outcomes):
        self.outcomes = deque(outcomes)

    def predict_with_confidence(self, features):
        outcome = self.outcomes[0] if len(self.outcomes) == 1 else self.outcomes.popleft()
        return [dict(outcome) for _ in range(len(features))]


def _classifier(model):
    clf = online.OnlineSliceClassifier.__new__(online.OnlineSliceClassifier)
    clf.qos, clf.cnn, clf.rf, clf.traffic, clf.window_s = FakeQos(), None, model, None, 5.0
    clf.enabled, clf.all_ues = True, True
    clf.decisions, clf.reclassifications, clf.deferrals, clf.abstentions = [], [], {}, 0
    clf.flows, clf.readers = {}, {}
    return clf


def _feed(clf, start, end, rate=20):
    """Append UDP packets of FLOW between two timestamps (as _ingest would)."""
    state = clf.flows.setdefault(FLOW, {"first_ts": start, "packets": deque(maxlen=online.FLOW_BUFFER),
                                        "class": None, "alt": None, "alt_count": 0, "checked": 0})
    t = start
    while t < end:
        state["packets"].append((t, FLOW, 1, 1200, 17, 0, 1172))
        state["last_ts"] = t
        t += 1 / rate


def test_flow_is_decided_early_once_seen_for_a_second(monkeypatch):
    clf = _classifier(ScriptedModel([{"predicted": "healthcare", "confidence": 0.9, "abstained": False, "reason": None}]))
    monkeypatch.setattr(clf, "_ingest", lambda: None)
    _feed(clf, 0.0, 0.6)
    clf.step(1)
    assert not clf.qos.flow_rules                       # 0.6 s: too early
    _feed(clf, 0.6, 1.3)
    clf.step(2)
    assert clf.qos.flow_rules[FLOW] == "healthcare"
    assert 1.0 <= clf.decisions[0]["observed_s"] < 1.5


def test_abstention_defers_then_falls_back(monkeypatch):
    clf = _classifier(ScriptedModel([{"predicted": "education", "confidence": 0.3, "abstained": True,
                                      "reason": "low_confidence"}]))
    monkeypatch.setattr(clf, "_ingest", lambda: None)
    _feed(clf, 0.0, 2.0)
    for tick in range(1, online.MAX_DEFERRALS):
        clf.step(tick)
        assert not clf.qos.flow_rules
    clf.step(online.MAX_DEFERRALS)
    assert clf.qos.flow_rules[FLOW] == FALLBACK_CLASS and clf.decisions[-1]["fallback"]


def test_reclassification_needs_confident_confirmed_disagreement(monkeypatch):
    early = {"predicted": "general", "confidence": 0.7, "abstained": False, "reason": None}
    later = {"predicted": "healthcare", "confidence": 0.95, "abstained": False, "reason": None}
    clf = _classifier(ScriptedModel([early, later]))
    monkeypatch.setattr(clf, "_ingest", lambda: None)
    _feed(clf, 0.0, 1.2)
    clf.step(1)
    assert clf.qos.flow_rules[FLOW] == "general"
    _feed(clf, 1.2, 7.0)
    clf.step(2 * online.RECHECK_TICKS)                  # first confident disagreement: not yet
    assert clf.qos.flow_rules[FLOW] == "general"
    _feed(clf, 7.0, 12.0)
    clf.step(3 * online.RECHECK_TICKS)                  # confirmed on the next check: rule replaced
    assert clf.qos.flow_rules[FLOW] == "healthcare" and clf.qos.calls[-1][2] is True
    assert clf.reclassifications[0]["from"] == "general"


def _pcap_record(ts, payload):
    return struct.pack("<IIII", int(ts), int((ts % 1) * 1e6), len(payload), len(payload)) + payload


def _ip_udp(src, dst):
    import dpkt
    udp = dpkt.udp.UDP(sport=40000, dport=5001, data=b"x" * 32)
    udp.ulen = len(bytes(udp))
    ip = dpkt.ip.IP(src=bytes(map(int, src.split("."))), dst=bytes(map(int, dst.split("."))), p=17, data=udp)
    ip.len = len(bytes(ip))
    return bytes(ip)


def test_incremental_reader_returns_only_new_complete_records(tmp_path):
    path = tmp_path / "ue.pcap"
    header = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 101)      # LINKTYPE_RAW
    pkt = _ip_udp("10.0.1.10", "10.0.2.10")
    first = _pcap_record(1.0, pkt) + _pcap_record(1.1, pkt)
    second = _pcap_record(1.2, pkt)
    path.write_bytes(header + first + second[:10])                        # last record half written
    reader = IncrementalCaptureReader(CapturePoint(str(path), "10.0.1.10"))
    assert [r[0] for r in reader.read_new()] == [1.0, pytest.approx(1.1)]
    path.write_bytes(header + first + second)
    rows = reader.read_new()
    assert len(rows) == 1 and rows[0][1] == "tx"
    assert reader.read_new() == []

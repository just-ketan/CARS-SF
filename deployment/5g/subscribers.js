// Provision one subscriber per service slice (Open5GS subscriber schema v1).
db = db.getSiblingDB("open5gs");
const slices = [
  ["999700000000001", 2, "000001", "health"],
  ["999700000000002", 1, "000002", "edu"],
  ["999700000000003", 3, "000003", "agri"],
  ["999700000000004", 1, "000004", "internet"],
];
const ambr = { downlink: { value: 1, unit: 3 }, uplink: { value: 1, unit: 3 } };
for (const [imsi, sst, sd, dnn] of slices) {
  db.subscribers.replaceOne({ imsi }, {
    schema_version: NumberInt(1), imsi, msisdn: [], imeisv: [], mme_host: [], mm_realm: [], purge_flag: [],
    security: { k: "465B5CE8B199B49FAA5F0A2EE238A6BC", op: null,
                opc: "E8ED289DEBA952E4283B54E88E6183CA", amf: "8000", sqn: NumberLong(97) },
    ambr,
    slice: [{ sst: NumberInt(sst), sd, default_indicator: true, session: [{
      name: dnn, type: NumberInt(3), ambr,
      qos: { index: NumberInt(9), arp: { priority_level: NumberInt(8),
             pre_emption_capability: NumberInt(1), pre_emption_vulnerability: NumberInt(1) } },
      pcc_rule: [] }] }],
    access_restriction_data: 32, network_access_mode: 0, subscriber_status: 0,
    operator_determined_barring: 0, subscribed_rau_tau_timer: 12, __v: 0,
  }, { upsert: true });
}
print("provisioned " + db.subscribers.countDocuments() + " subscribers");

from traffic.traffic_factory import TrafficFactory

print(TrafficFactory.available_applications())

profile = TrafficFactory.get("zoom")

print(profile)
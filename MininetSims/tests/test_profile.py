from traffic.applications.education import ZOOM_CLASS


print()

print(ZOOM_CLASS)

print()

print("Application :", ZOOM_CLASS.application_name)

print("Service :", ZOOM_CLASS.service_class.value)

print("Protocol :", ZOOM_CLASS.transport_protocol.value)

print("QoS :", ZOOM_CLASS.qos_class.value)

print()
from traffic.applications.education import ZOOM_CLASS


class TrafficFactory:

    _applications = {
        "zoom": ZOOM_CLASS,
    }

    @classmethod
    def get(cls, application_name: str):

        key = application_name.lower()

        if key not in cls._applications:
            raise ValueError(f"Unknown application '{application_name}'")

        return cls._applications[key]

    @classmethod
    def available_applications(cls):

        return list(cls._applications.keys())
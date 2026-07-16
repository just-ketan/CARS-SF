from traffic_generator.common.config_loader import ConfigLoader


def test_loading():

    services = ConfigLoader.load_directory("configs")

    assert len(services) == 4

    assert services[0].name is not None
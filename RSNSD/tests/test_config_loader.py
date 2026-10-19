import os

from RSNSD.traffic_generator.common.config_loader import ConfigLoader

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs")


def test_loading():

    services = ConfigLoader.load_directory(CONFIG_DIR)

    assert len(services) == 4

    assert services[0].name is not None

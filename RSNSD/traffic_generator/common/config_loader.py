# read yaml, validate fields, convert yaml to python objects, raise errors if invalid

from pathlib import Path
import yaml
from .models import Service

class ConfigLoader:
    @staticmethod
    def load(path:str) -> Service:
        """
        Load a YAML configuration file and convert it to a Service object.

        Args:
            path (str): The path to the YAML configuration file.
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return Service.model_validate(data)

    @staticmethod
    def load_directory(directory: str):

        services = []

        for file in Path(directory).glob("*.yaml"):
            services.append(ConfigLoader.load(file))

        return services
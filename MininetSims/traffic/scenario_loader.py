from pathlib import Path
import yaml


class ScenarioLoader:

    BASE = Path("configs/scenarios")

    @classmethod
    def load(cls, name):

        path = cls.BASE / f"{name}.yaml"

        with open(path) as f:
            return yaml.safe_load(f)
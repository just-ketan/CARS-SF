import json
from pathlib import Path


def save_json(data, filename):
    filename = Path(filename)

    filename.parent.mkdir(parents=True, exist_ok=True)

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def load_json(filename):
    with open(filename) as f:
        return json.load(f)
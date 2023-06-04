import tomllib
from typing import Any


def load_toml(file: str) -> dict[str, Any]:
    with open(file, "rb") as config_file:
        return tomllib.load(config_file)

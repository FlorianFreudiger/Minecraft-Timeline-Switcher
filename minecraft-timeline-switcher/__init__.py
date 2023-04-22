from __future__ import annotations

import os
import tomllib
import logging
from typing import Any

from models import Variant
from packwiz import PackwizSyncer
from portainer import Portainer


class Config:
    timeline: list[Variant]
    interval: int
    start_time: str

    def __init__(self, interval: int, start_time: str, timeline: list[Variant]) -> None:
        self.interval = interval
        self.start_time = start_time
        self.timeline = timeline

    @staticmethod
    def from_config(config: dict[str, Any]) -> Config:
        interval = config["updates"]["interval"]
        start_time = config["updates"]["start_time"]
        timeline = []

        pack = None
        server_image = None
        server_type = "VANILLA"
        server_version = "packwiz"

        for variant in config["variant"]:
            if "pack" in variant:
                pack = variant["pack"]
            if "server_image" in variant:
                server_image = variant["server_image"]
            if "server_type" in variant:
                server_type = variant["server_type"]
            if "server_version" in variant:
                server_version = variant["server_version"]

            if pack is None or server_image is None or server_type is None or server_version is None:
                raise ValueError("Missing variant information."
                                 "Make sure the first variant has at least a pack and server_image.")
            timeline.append(Variant(pack, server_image, server_type, server_version))

        return Config(interval, start_time, timeline)


def load_toml(file: str) -> dict[str, Any]:
    with open(file, "rb") as config_file:
        return tomllib.load(config_file)


def main() -> None:
    config_dict = load_toml("../config/config.toml")
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s', level=config_dict["verbosity"])

    config = Config.from_config(config_dict)

    update_targets = []

    if config_dict["packwiz"]["enable"]:
        update_targets.append(PackwizSyncer.from_config(config_dict))

    if config_dict["portainer"]["enable"]:
        secrets_dict = load_toml("../config/secrets.toml")
        update_targets.append(Portainer.from_config(config_dict, secrets_dict))

    logging.debug("Loading configs complete.")

    if not os.path.isfile("../config/docker-compose-template.yml"):
        raise FileNotFoundError("docker-compose-template.yml missing.")

    variant = config.timeline[0]
    for target in update_targets:
        target.update_variant(variant)


if __name__ == "__main__":
    main()

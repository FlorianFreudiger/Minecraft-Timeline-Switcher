from __future__ import annotations

import os
import tomllib
import logging
from typing import Any

from portainer import Portainer


class Variant:
    pack: str
    server_image: str
    server_type: str
    server_version: str

    def __init__(self, pack: str, server_image: str, server_type: str, server_version: str) -> None:
        self.pack = pack
        pack_path = os.path.join("timeline", pack)
        if not os.path.isdir(pack_path):
            raise FileNotFoundError(f"Pack {pack} not found in timeline directory.")

        self.server_image = server_image
        self.server_type = server_type

        if server_version == "packwiz":
            with open(os.path.join(pack_path, "pack.toml"), "rb") as pack_toml_file:
                pack_toml = tomllib.load(pack_toml_file)
                self.server_version = pack_toml["versions"]["minecraft"]
        else:
            self.server_version = server_version

    def generate_compose(self) -> str:
        with open("docker-compose-template.yml", "r") as template:
            compose = template.read()
            return compose.format(server_image=self.server_image,
                                  server_type=self.server_type,
                                  server_version=self.server_version)


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
    config_dict = load_toml("config.toml")
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s', level=config_dict["verbosity"])

    config = Config.from_config(config_dict)

    compose = config.timeline[0].generate_compose()

    if config_dict["portainer"]["enable"]:
        secrets_dict = load_toml("secrets.toml")
        portainer = Portainer.from_config(config_dict, secrets_dict)
        portainer.update_stack(compose)

    logging.debug("Loading configs complete.")

    if not os.path.isfile("docker-compose-template.yml"):
        raise FileNotFoundError("docker-compose-template.yml missing.")

    print(compose)


if __name__ == "__main__":
    main()

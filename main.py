from __future__ import annotations

import os
import tomllib


class Variant:
    pack: str
    server_image: str
    server_type: str
    server_version: str

    def __init__(self, pack: str, server_image: str, server_type: str, server_version: str) -> None:
        self.pack = pack
        pack_path = os.path.join("timeline", pack)
        if not os.path.isdir(pack_path):
            print(f"Pack {pack} not found in timeline directory.")
            exit(1)

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

    @staticmethod
    def load_from_file(file: str) -> Config:
        with open(file, "rb") as config_file:
            config = tomllib.load(config_file)

            return Config(config)

    def __init__(self, config: dict) -> None:
        updates = config["updates"]
        self.interval = updates["interval"]
        self.start_time = updates["start_time"]
        self.timeline = []

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
                print("Missing variant information. Make sure the first variant has at least a pack and server_image.")
                exit(1)
            self.timeline.append(Variant(pack, server_image, server_type, server_version))


def main() -> None:
    config = Config.load_from_file("config.toml")

    if not os.path.isfile("docker-compose-template.yml"):
        print("docker-compose-template.yml missing.")
        exit(1)

    compose = config.timeline[0].generate_compose()
    print(compose)


if __name__ == "__main__":
    main()

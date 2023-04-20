from __future__ import annotations

import os
import tomllib
from packaging import version


class Config:
    versions: list[str]
    interval: int
    start_time: str
    upgrades: dict[version.Version, str]

    @staticmethod
    def load_from_file(file: str) -> Config:
        with open(file, "rb") as config_file:
            config = tomllib.load(config_file)

            return Config(config)

    def __init__(self, config: dict) -> None:
        updates = config["updates"]
        self.versions = updates["versions"]
        self.interval = updates["interval"]
        self.start_time = updates["start_time"]
        self.upgrades = {}
        for upgrade in config["upgrades"]:
            self.upgrades[version.parse(upgrade["minecraft_version"])] = upgrade["server_image"]

    def check_versions(self):
        for pack in self.versions:
            version_path = os.path.join("versions", pack)
            pack_toml_path = os.path.join(version_path, "pack.toml")
            if not os.path.isdir(version_path):
                print(f"Version {pack} not found in versions directory.")
                exit(1)
            if not os.path.isfile(pack_toml_path):
                print(f"pack.toml not found in {version_path} directory.")
                exit(1)


def get_minecraft_version(variant: str) -> version.Version:
    pack_toml_path = os.path.join("versions", variant, "pack.toml")

    with open(pack_toml_path, "rb") as pack_toml_file:
        pack_toml = tomllib.load(pack_toml_file)
        return version.parse(pack_toml["versions"]["minecraft"])


def get_server_image(config: Config, target_minecraft_version: version.Version) -> str:
    latest_image = None
    for minecraft_version, image in config.upgrades.items():
        if target_minecraft_version >= minecraft_version:
            latest_image = image

    if latest_image is None:
        print("No server image found for minecraft version", target_minecraft_version)
        exit(1)

    return latest_image


def generate_compose(minecraft_version: version.Version, server_image: str) -> str:
    with open("docker-compose-template.yml", "r") as template:
        compose = template.read()
        return compose.format(minecraft_version=minecraft_version,
                              server_image=server_image)


def main() -> None:
    config = Config.load_from_file("config.toml")
    config.check_versions()

    if not os.path.isfile("docker-compose-template.yml"):
        print("docker-compose-template.yml missing.")
        exit(1)

    minecraft_version = get_minecraft_version(config.versions[0])
    server_image = get_server_image(config, minecraft_version)
    compose = generate_compose(minecraft_version, server_image)
    print(compose)


if __name__ == "__main__":
    main()

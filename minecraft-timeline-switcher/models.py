from __future__ import annotations

import os
import tomllib
from abc import ABC, abstractmethod


class UpdateTarget(ABC):
    @abstractmethod
    def update_variant(self, variant: Variant) -> None:
        pass


class Variant:
    pack: str
    server_image: str
    server_type: str
    server_version: str

    def __init__(self, pack: str, server_image: str, server_type: str, server_version: str) -> None:
        self.pack = pack
        pack_path = os.path.join("../config/packwiz", pack)
        if not os.path.isdir(pack_path):
            raise FileNotFoundError(f"Pack {pack} not found in packwiz directory.")

        self.server_image = server_image
        self.server_type = server_type

        if server_version == "packwiz":
            with open(os.path.join(pack_path, "pack.toml"), "rb") as pack_toml_file:
                pack_toml = tomllib.load(pack_toml_file)
                self.server_version = pack_toml["versions"]["minecraft"]
        else:
            self.server_version = server_version

    def generate_compose(self) -> str:
        with open("../config/docker-compose-template.yml", "r") as template:
            compose = template.read()
            return compose.format(server_image=self.server_image,
                                  server_type=self.server_type,
                                  server_version=self.server_version)

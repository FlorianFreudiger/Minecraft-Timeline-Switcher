from __future__ import annotations

import os
import tomllib
from abc import ABC, abstractmethod
from typing import Any

from packaging import version


class UpdateTarget(ABC):
    @abstractmethod
    def update_variant(self, variant: Variant) -> None:
        pass


class Variant:
    pack: str
    server_image: str
    server_type: str
    server_version: str
    server_additional_envs: dict[str, str]

    def __init__(self, pack: str,
                 server_image: str, server_type: str, server_version: str, server_additional_envs: dict) -> None:
        self.pack = pack
        pack_path = os.path.join("../config/packwiz", pack)
        if not os.path.isdir(pack_path):
            raise FileNotFoundError(f"Pack {pack} not found in packwiz directory.")

        self.server_image = server_image
        self.server_type = server_type

        if server_version.lower() == "packwiz":
            with open(os.path.join(pack_path, "pack.toml"), "rb") as pack_toml_file:
                pack_toml = tomllib.load(pack_toml_file)
                self.server_version = pack_toml["versions"]["minecraft"]
        else:
            self.server_version = server_version

        self.server_additional_envs = server_additional_envs

    def __str__(self) -> str:
        return f"Variant: Pack \"{self.pack}\", Server using {self.server_type} {self.server_version}"

    def parse_server_version(self) -> version.Version:
        version_string = self.server_version.strip()

        # Handle bukkit version strings
        if self.server_type.strip().casefold() == "bukkit":
            version_string = version_string.split("-", maxsplit=1)[0]

        return version.parse(version_string)

    def generate_compose(self, template_path: str) -> str:
        with open(template_path, "r") as template:
            compose = template.read()

            additional_envs = ""
            for key, value in self.server_additional_envs.items():
                additional_envs += f"\n            - {key}={value}"

            return compose.format(server_image=self.server_image,
                                  server_type=self.server_type,
                                  server_version=self.server_version,
                                  server_additional_envs=additional_envs)

    @staticmethod
    def list_from_config(config: dict[str, Any]) -> list[Variant]:
        variants = []

        pack = None
        server_image = None
        server_type = "VANILLA"
        server_version = "packwiz"
        server_additional_envs = {}

        for variant in config["variants"]:
            if "pack" in variant:
                pack = variant["pack"]
            if "server_image" in variant:
                server_image = variant["server_image"]
            if "server_type" in variant:
                server_type = variant["server_type"]
            if "server_version" in variant:
                server_version = variant["server_version"]
            if "server_additional_envs" in variant:
                server_additional_envs = variant["server_additional_envs"]

            if pack is None or server_image is None or server_type is None or server_version is None:
                raise ValueError("Missing variant information."
                                 "Make sure the first variant has at least a pack and server_image.")
            variants.append(Variant(pack, server_image, server_type, server_version, server_additional_envs))

        return variants

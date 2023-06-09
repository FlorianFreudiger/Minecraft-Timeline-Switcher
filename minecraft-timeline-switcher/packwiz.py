from __future__ import annotations

import os
import shutil
import logging
from typing import Any

from models import UpdateTarget, Variant


class PackwizSyncer(UpdateTarget):
    output_path: str

    @staticmethod
    def from_config(config: dict[str, Any]) -> PackwizSyncer:
        path = os.path.join("..", config["packwiz"]["output_path"])
        return PackwizSyncer(path)

    def __init__(self, output_path: str) -> None:
        self.output_path = output_path

    def update_variant(self, variant: Variant) -> None:
        pack_path = os.path.join("../config/packwiz", variant.pack)
        logging.debug(f"Copying pack \"%s\" to \"%s\"", variant.pack, self.output_path)
        shutil.copytree(pack_path, self.output_path, dirs_exist_ok=True)

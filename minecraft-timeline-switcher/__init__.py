from __future__ import annotations

import logging
import tomllib
from typing import Any

from models import Variant, UpdateTarget
from packwiz import PackwizSyncer
from portainer import Portainer


class Updater:
    timeline: list[Variant]
    interval: int
    start_time: str
    targets: list[UpdateTarget]

    @staticmethod
    def from_config(config: dict[str, Any], secrets: dict[str, Any]) -> Updater:
        interval = config["updates"]["interval"]
        start_time = config["updates"]["start_time"]
        timeline = Variant.list_from_config(config)

        update_targets = []
        if config["packwiz"]["enable"]:
            update_targets.append(PackwizSyncer.from_config(config))
        if config["portainer"]["enable"]:
            # Add portainer last to ensure packwiz output is already in place if used in compose template
            update_targets.append(Portainer.from_config(config, secrets))

        return Updater(interval, start_time, timeline, update_targets)

    def __init__(self, interval: int, start_time: str, timeline: list[Variant], targets: list[UpdateTarget]) -> None:
        self.interval = interval
        self.start_time = start_time
        self.timeline = timeline
        self.targets = targets

    def update(self, variant: Variant) -> None:
        for target in self.targets:
            target.update_variant(variant)


def load_toml(file: str) -> dict[str, Any]:
    with open(file, "rb") as config_file:
        return tomllib.load(config_file)


def main() -> None:
    config = load_toml("../config/config.toml")
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s', level=config["verbosity"])

    secrets = load_toml("../config/secrets.toml")
    updater = Updater.from_config(config, secrets)

    logging.debug("Loading configs complete.")
    updater.update(updater.timeline[0])


if __name__ == "__main__":
    main()

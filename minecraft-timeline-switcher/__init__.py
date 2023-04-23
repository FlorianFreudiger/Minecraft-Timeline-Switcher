from __future__ import annotations

import logging
import time
import tomllib
import schedule
from typing import Any

from models import Variant, UpdateTarget
from packwiz import PackwizSyncer
from portainer import Portainer


class Updater:
    timeline: list[Variant]
    interval: int
    start_time: str
    targets: list[UpdateTarget]

    next_variant: int

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
        self.next_variant = 0

    def update(self, variant: Variant) -> None:
        for target in self.targets:
            target.update_variant(variant)

    def first_job(self):
        logging.debug("Start time reached, scheduling future updates every %s minutes", self.interval)
        schedule.every(self.interval).minutes.do(self.update_job)

        # Run first update after scheduling to not influence update times
        logging.debug("Running first update")
        first_update_job_result = self.update_job()
        if first_update_job_result is schedule.CancelJob:
            logging.debug("First update already finished the timeline, cancelling future jobs.")
            schedule.clear()

        return schedule.CancelJob

    def update_job(self):
        variant = self.timeline[self.next_variant]
        logging.info("Updating to %s", variant)
        self.update(variant)

        self.next_variant += 1
        if self.next_variant >= len(self.timeline):
            logging.info("Last update finished")

            return schedule.CancelJob

    def initialize_schedule(self) -> None:
        if self.start_time.lower() == "now":
            logging.info("Scheduling start now, afterwards every %s minutes", self.interval)
            self.first_job()
            return

        logging.info("Scheduling start at %s, afterwards every %s minutes", self.start_time, self.interval)
        schedule.every().day.at(self.start_time).do(self.first_job)


def load_toml(file: str) -> dict[str, Any]:
    with open(file, "rb") as config_file:
        return tomllib.load(config_file)


def main() -> None:
    config = load_toml("../config/config.toml")
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s', level=config["verbosity"])

    secrets = load_toml("../config/secrets.toml")
    updater = Updater.from_config(config, secrets)

    logging.debug("Loading configs complete.")

    updater.initialize_schedule()

    if schedule.jobs:
        logging.debug("Waiting for first job")
        schedule.run_pending()
    while schedule.jobs:
        time.sleep(10)
        schedule.run_pending()
    logging.debug("Timeline finished, exiting")


if __name__ == "__main__":
    main()

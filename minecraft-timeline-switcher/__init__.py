from __future__ import annotations

import os
import logging
import time
import tomllib
from typing import Any

import schedule
from packaging import version

from save import UpdaterSaver
from models import Variant, UpdateTarget
from packwiz import PackwizSyncer
from portainer import Portainer


class Updater:
    saver: UpdaterSaver
    variants: list[Variant]
    interval: int
    start_time: str
    targets: list[UpdateTarget]

    next_variant_index: int

    @staticmethod
    def from_config(config: dict[str, Any], secrets: dict[str, Any]) -> Updater:
        interval = config["updater"]["interval"]
        start_time = config["updater"]["start_time"]

        variants = []
        timeline_names = config["updater"]["timelines"]
        for timeline_name in timeline_names:
            path = os.path.join("../config", timeline_name + ".toml")
            timeline_config = load_toml(path)

            if "variants" not in timeline_config:
                logging.info("Found no variants in timeline \"%s\", skipping", timeline_name)
                continue

            timeline_variants = Variant.list_from_config(timeline_config)
            variants += timeline_variants
            logging.info("Found %d variants in timeline \"%s\"", len(timeline_variants), timeline_name)

        # Enumerate for loop
        last_server_version = None
        for index, variant in enumerate(variants):
            logging.info("Parsed variant %02d: %s", index, variant)

            try:
                server_version = version.parse(variant.server_version)
                if last_server_version is not None and server_version < last_server_version:
                    logging.warning("Variant %02d seems to have a lower server version than the previous variant "
                                    "(%s -> %s). Be careful, your world may not load correctly!",
                                    index, last_server_version, server_version)
                last_server_version = server_version
            except version.InvalidVersion:
                logging.warning("Cannot verify that variant %02d is not a downgrade, "
                                "due to unsupported version format: \"%s\"", index, variant.server_version)

            variant.index = index

        update_targets = []
        if config["packwiz"]["enable"]:
            update_targets.append(PackwizSyncer.from_config(config))
        if config["portainer"]["enable"]:
            # Add portainer last to ensure packwiz output is already in place if used in compose template
            update_targets.append(Portainer.from_config(config, secrets))

        saver = UpdaterSaver.from_config(config)

        return Updater(interval, start_time, variants, update_targets, saver)

    def __init__(self, interval: int, start_time: str, variants: list[Variant], targets: list[UpdateTarget],
                 saver: UpdaterSaver) -> None:
        self.interval = interval
        self.start_time = start_time
        self.variants = variants
        self.targets = targets

        self.saver = saver
        self.next_variant_index = saver.load_progress()

    def update(self, variant: Variant) -> None:
        for target in self.targets:
            target.update_variant(variant)

    def next_variant(self) -> Variant:
        return self.variants[self.next_variant_index]

    def is_finished(self) -> bool:
        return self.next_variant_index >= len(self.variants)

    def finish(self) -> None:
        self.saver.delete_progress()

    def first_job(self):
        logging.debug("Start time reached, scheduling future updates every %s minutes", self.interval)
        scheduled_updates = schedule.every(self.interval).minutes.do(self.update_job)

        # Run first update after scheduling to not influence update times
        logging.debug("Running first update")
        first_update_job_result = self.update_job()
        if first_update_job_result is schedule.CancelJob:
            logging.debug("First update already finished the timeline, cancelling future jobs.")
            schedule.cancel_job(scheduled_updates)

        return schedule.CancelJob

    def update_job(self):
        variant = self.next_variant()
        logging.info("Updating to %s", variant)
        self.update(variant)

        self.saver.save_progress(self.next_variant_index)

        self.next_variant_index += 1
        if self.is_finished():
            logging.info("Last update finished")
            self.finish()

            return schedule.CancelJob

        next_variant = self.next_variant()
        logging.info("Next update in %s minutes: %s", self.interval, next_variant)

    def initialize_schedule(self) -> None:
        if self.is_finished():
            logging.info("Last update already finished, exiting")
            self.finish()
            return

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

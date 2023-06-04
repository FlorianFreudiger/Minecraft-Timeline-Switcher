from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Any, Type

import schedule
from packaging import version
from schedule import CancelJob

from models import Variant, UpdateTarget
from packwiz import PackwizSyncer
from portainer import Portainer
from save import UpdaterSaver
from utility import load_toml


class UpdateQueue:
    queue: queue.Queue
    thread: threading.Thread

    def __init__(self) -> None:
        self.queue = queue.Queue()
        # Daemon thread to not block program exit when KeyboardInterrupt is raised
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def worker(self) -> None:
        while True:
            job = self.queue.get()
            job()
            self.queue.task_done()

    def wait_for_finish(self) -> None:
        self.queue.join()

    def put(self, job) -> None:
        self.queue.put(job)


class Updater:
    saver: UpdaterSaver
    variants: list[Variant]
    interval: int
    start_time: str
    targets: list[UpdateTarget]

    next_variant_index: int

    scheduler: schedule.Scheduler
    update_queue: UpdateQueue

    @staticmethod
    def from_config(config: dict[str, Any]) -> Updater:
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
                server_version = variant.parse_server_version()
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
            update_targets.append(Portainer.from_config(config))

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

        self.scheduler = schedule.Scheduler()
        self.update_queue = UpdateQueue()

    def next_variant(self) -> Variant:
        return self.variants[self.next_variant_index]

    def is_finished(self) -> bool:
        return self.next_variant_index >= len(self.variants)

    def finish(self) -> None:
        self.scheduler.clear()
        self.update_queue.wait_for_finish()
        self.saver.delete_progress()

    def first_job(self) -> Type[CancelJob]:
        # Run first update after scheduling to not influence update times
        logging.debug("Running first update")
        self.update_queue.put(self.update_job)

        logging.debug("Scheduling future updates every %s minutes", self.interval)
        self.scheduler.every(self.interval).minutes.do(self.update_queue.put, self.update_job)

        return schedule.CancelJob

    def update_job(self) -> None:
        variant = self.next_variant()
        logging.info("Updating to %s", variant)

        for target in self.targets:
            target.update_variant(variant)

        self.saver.save_progress(self.next_variant_index)

        self.next_variant_index += 1
        if self.is_finished():
            logging.info("Last update finished")
            self.finish()

        next_update = self.scheduler.next_run
        assert next_update is not None

        logging.info("Next update at %s to %s", next_update.strftime("%Y-%m-%d %H:%M:%S"), self.next_variant())

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
        self.scheduler.every().day.at(self.start_time).do(self.first_job)

    def run(self, scheduler_interval: int) -> None:
        self.initialize_schedule()

        if self.scheduler.jobs:
            logging.debug("Waiting for first job")
            self.scheduler.run_pending()
        while self.scheduler.jobs:
            time.sleep(scheduler_interval)
            self.scheduler.run_pending()

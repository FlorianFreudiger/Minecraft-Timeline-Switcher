from __future__ import annotations

import os
import logging
from typing import Any


class UpdaterSaver:
    enable: bool
    path: str
    repeat_after_load: bool
    keep: bool

    @staticmethod
    def from_config(config: dict[str, Any]) -> UpdaterSaver:
        enable = config["updates"]["save"]["enable"]
        path = os.path.join("..", config["updates"]["save"]["path"])
        keep = config["updates"]["save"]["keep"]

        repeat_after_load = config["updates"]["save"]["repeat_after_load"]
        if type(repeat_after_load) is str and repeat_after_load.lower() == "auto":
            repeat_after_load = config["updates"]["start_time"].lower() == "now"
        elif type(repeat_after_load) is not bool:
            raise ValueError("repeat_after_load must be a boolean or the string \"auto\"")

        return UpdaterSaver(enable, path, repeat_after_load, keep)

    def __init__(self, enable: bool, path: str, repeat_after_load: bool, keep: bool) -> None:
        self.enable = enable
        self.path = path
        self.repeat_after_load = repeat_after_load
        self.keep = keep

    def load_progress(self) -> int:
        if not self.enable:
            return 0

        try:
            with open(self.path, "r") as last_update_file:
                progress = int(last_update_file.read())
                if not self.repeat_after_load:
                    progress += 1
                logging.info("Loaded save file, will continue at variant %02d, "
                             "delete/modify \"%s\" or disable saving to restart/adjust timeline", progress, self.path)
                return progress

        except FileNotFoundError:
            logging.debug("No progress file found, starting from beginning")
            return 0

    def save_progress(self, index: int) -> None:
        if not self.enable:
            return

        logging.debug("Saving progress %02d to file", index)
        with open(self.path, "w") as last_update_file:
            last_update_file.write(str(index))

    def delete_progress(self) -> None:
        if self.keep:
            logging.debug("Keeping save file at \"%s\"", self.path)
            return

        try:
            os.remove(self.path)
            logging.debug("Deleted save file at \"%s\"", self.path)
        except FileNotFoundError:
            pass

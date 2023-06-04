from __future__ import annotations

import logging

from update import Updater
from utility import load_toml


def main() -> None:
    config = load_toml("../config/config.toml")
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s', level=config["verbosity"])

    updater = Updater.from_config(config)
    logging.debug("Loading config complete.")

    updater.run(10)
    logging.info("Timeline finished, exiting")


if __name__ == "__main__":
    main()

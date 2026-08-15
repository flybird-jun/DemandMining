import logging

import json
from pathlib import Path

cur_dir = Path(__file__).resolve().parents[0]
config_path =  cur_dir / "config.json"
config_example_path = cur_dir / "config.example.json"

if config_path.exists():
    config = json.loads(config_path.read_text())
else:
    config = json.loads(config_example_path.read_text())

logging.basicConfig(
            filename = config["log_path"] + "/run.log",
            level = logging.WARNING,
            format = "%(asctime)s.%(msecs)03d | [%(levelname)s] | %(message)s",
            datefmt = "%Y-%m-%d %H:%M:%S",
            encoding = "utf-8")
logger = logging.getLogger("demandmining")

class ParentException(Exception):
    pass

class UninitedException(Exception):
    pass
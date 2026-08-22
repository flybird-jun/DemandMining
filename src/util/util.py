import logging
import json
import shutil
from pathlib import Path

config_dir_path = Path(__file__).resolve().parents[2] / "run"

config_path = config_dir_path / "config.json"
config = json.loads(config_path.read_text())
# 加载logger
logging.basicConfig(
    filename = config["log_path"] + "/run.log",
    level = logging.WARNING,
    format = "%(asctime)s.%(msecs)03d | [%(levelname)s] | %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    encoding = "utf-8")
logger = logging.getLogger("demandmining")

class UninitedException(Exception):
    pass
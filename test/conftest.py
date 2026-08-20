import pytest
from pathlib import Path
import shutil
import os
import time
# @pytest.fixture(autouse=True)
def pytest_configure(config):
    if config.option.collectonly:
        return
     
    src = Path(__file__).resolve().parents[0] / "config.json" 
    dst_dir = Path(__file__).resolve().parents[1] / "run"
    shutil.copy(src, dst_dir)
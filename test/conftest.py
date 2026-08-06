from pathlib import Path
from common.config import settings
def pytest_configure(config):
    if config.option.collectonly:
        return
    settings.PG_DATABASE = "test"
    settings.DEBUG = "ON"

    

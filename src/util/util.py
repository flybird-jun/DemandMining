import logging
import asyncio
from logging.handlers import RotatingFileHandler
from pathlib import Path

class TaskNameFilter(logging.Filter):
    def filter(self, record):
        try:
            task = asyncio.current_task()
            record.task_name = task.get_name() if task else "main"
        except RuntimeError:
            record.task_name = "main"
        return True
    
def setup_logging():
    # 根的logger
    logger = logging.getLogger()
    # 防止重复初始化
    if logger.handlers:
        return
    cwd = Path.cwd()
    log_dir = cwd / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=log_dir / "run.log",
        maxBytes=10 * 1024 * 1024,   # 10MB
        backupCount=16,               # 保留16个历史文件
        encoding="utf-8"
    )
     # 日志格式
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | [task=%(task_name)s] | %(name)s | %(message)s")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(TaskNameFilter())
    
    logger.addHandler(file_handler)
    logger.setLevel(logging.WARNING)
    

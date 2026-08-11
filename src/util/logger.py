import logging
def log_init(path:str):
    logging.basicConfig(
            filename=path,
            level = logging.WARNING,
            format="%(asctime)s.%(msecs)03d | [%(levelname)s] | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            encoding = "utf-8")
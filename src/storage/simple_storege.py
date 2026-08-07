from datetime import datetime
import json
class storage:
    def __init__(self):
        pass
    
    def save_article(self, data:dict) -> None:
        now = datetime.now()
        timestamp = now.strftime("%Y_%m_%d_%H_%M_%S_%f")
        timestamp = timestamp[:-3]
        with open(timestamp, "w", encoding="utf-8") as fd:
            json.dump(data, fd, ensure_ascii = False, indent = 4)
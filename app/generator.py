import random
import time
import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "/var/log/app"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(LOG_FILE, maxBytes=500000, backupCount=3)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

ERROR_MESSAGES = [
    "Failed to process item id=%d due to timeout",
    "Unhandled exception in worker id=%d: NullReference",
    "Disk quota exceeded for user id=%d",
]

WARN_MESSAGES = [
    "High latency detected for endpoint /api/v1/items",
    "Retrying operation after transient failure id=%d",
    "Backpressure detected in pipeline stage %d",
]

INFO_MESSAGES = [
    "Worker %d processed item id=%d in 120ms",
    "Scheduled maintenance job started",
    "Heartbeat OK for worker %d",
]

def generate_line():
    r = random.random()
    if r < 0.7:
        return "INFO", random.choice(INFO_MESSAGES) % (random.randint(1, 10), random.randint(1000,9999))
    elif r < 0.9:
        return "WARN", random.choice(WARN_MESSAGES) % (random.randint(1,5))
    else:
        return "ERROR", random.choice(ERROR_MESSAGES) % (random.randint(100,999))

def main():
    while True:
        level, msg = generate_line()
        if level == "INFO":
            logger.info(msg)
        elif level == "WARN":
            logger.warning(msg)
        else:
            logger.error(msg)
        # variable sleep to create bursts
        time.sleep(random.uniform(0.05, 0.8))

if __name__ == "__main__":
    main()


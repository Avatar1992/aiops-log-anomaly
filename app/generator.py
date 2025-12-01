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
    """Generate random INFO / WARN / ERROR log lines."""
    p = random.random()

    if p < 0.7:
        # INFO logs (most common)
        template = random.choice(INFO_MESSAGES)
        try:
            msg = template % (random.randint(1, 10), random.randint(1000, 9999))
        except TypeError:
            msg = template
        return "INFO", msg

    elif p < 0.9:
        # WARN logs
        template = random.choice(WARN_MESSAGES)
        try:
            msg = template % random.randint(1, 10)
        except TypeError:
            msg = template
        return "WARN", msg

    else:
        # ERROR logs
        template = random.choice(ERROR_MESSAGES)
        try:
            msg = template % random.randint(1, 10)
        except TypeError:
            msg = template
        return "ERROR", msg


def main():
    while True:
        level, msg = generate_line()

        if level == "INFO":
            logger.info(msg)
        elif level == "WARN":
            logger.warning(msg)
        else:
            logger.error(msg)

        time.sleep(random.uniform(0.5, 2))  # adjustable rate


if __name__ == "__main__":
    main()

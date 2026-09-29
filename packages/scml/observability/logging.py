import json
import logging
import time
from uuid import uuid4

logger = logging.getLogger("scml")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def log(event, **fields):
    logger.info(json.dumps({"event": event, "time": time.time(), **fields}, default=str))


def trace_id():
    return uuid4().hex

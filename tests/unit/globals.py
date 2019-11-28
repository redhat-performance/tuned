import logging
import tuned.logs

logger = logging.getLogger()
handler = logging.NullHandler()
logger.addHandler(handler)

tuned.logs.get = lambda: logger

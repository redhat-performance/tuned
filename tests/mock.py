import flexmock
import logging
import tuned.logs

logger = logging.getLogger()
handler = logging.NullHandler()
logger.addHandler(handler)

flexmock.flexmock(tuned.logs).should_receive("get").and_return(logger)

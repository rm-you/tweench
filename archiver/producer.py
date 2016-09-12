from archiver import messages
from archiver import clients
from archiver import constants
import logging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class Producer(object):
    def add_subreddit(self, subreddit_name):
        LOG.info("Beginning to archive subreddit: {subreddit}"
                 .format(subreddit=subreddit_name))
        m = messages.SubredditMessage(subreddit_name)
        m.enqueue(clients.sqs_client(constants.QUEUE_NAME))

    def has_subreddit(self, subreddit_name):
        LOG.info("Checking for subreddit: {subreddit}"
                 .format(subreddit=subreddit_name))
        return False

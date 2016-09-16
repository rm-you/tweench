import logging

from archiver import clients
from archiver import config
from archiver import messages

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class Producer(object):
    def __init__(self):
        self.conf = config.get_config()

    def add_subreddit(self, subreddit_name, query_type, num):
        LOG.info("Beginning to archive {num} {type} from subreddit: {sub}"
                 .format(type=query_type, sub=subreddit_name, num=num))
        m = messages.SubredditMessage(subreddit_name, query_type, num)
        m.enqueue(clients.sqs_client(self.conf.QUEUE_NAME))

    def has_subreddit(self, subreddit_name):
        LOG.info("Checking for subreddit: {subreddit}"
                 .format(subreddit=subreddit_name))
        return False

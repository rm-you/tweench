import json
import logging

from archiver import constants

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class QueueMessage(object):
    id = None
    type = None
    body = None

    def enqueue(self, client):
        LOG.debug(u"Enqueueing message: {msg}"
                  .format(msg=str(self)))
        client.send_message(str(self))

    def finish(self, client):
        if not self.id:
            raise AttributeError("Message has no ID!")
        LOG.debug(u"Deleting message: {msg}".format(msg=str(self)))
        client.delete_message(self.id)

    def __str__(self):
        data = {
            "body": self.body,
            "type": self.type
        }
        if self.id:
            data.update({"mid": self.id})
        return json.dumps(data)


class SubredditMessage(QueueMessage):
    def __init__(self, subreddit_name, query_type=constants.QUERY_TOP_ALL_TIME,
                 query_num=10, mid=None):
        LOG.debug(u"Created new SubredditMessage: {subreddit}"
                  .format(subreddit=subreddit_name))
        self.type = constants.MESSAGE_SUBREDDIT
        self.subreddit_name = subreddit_name
        self.query_type = query_type
        self.query_num = query_num
        self.id = mid

    @property
    def body(self):
        return {
            "subreddit_name": self.subreddit_name,
            "query_type": self.query_type,
            "query_num": self.query_num
        }


class PostMessage(QueueMessage):
    def __init__(self, post_link, mid=None):
        LOG.debug(u"Created new PostMessage: {post}"
                  .format(post=post_link))
        self.type = constants.MESSAGE_POST
        self.post_link = post_link
        self.id = mid

    @property
    def body(self):
        return {
            "post_link": self.post_link
        }

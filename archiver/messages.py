import logging
import json
from archiver import constants

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class QueueMessage(object):
    id = None
    type = None
    body = None

    def enqueue(self, client):
        LOG.info("Enqueueing message: ({type}) {body}"
                 .format(type=self.type, body=self.body))
        client.send_message(
            str(self)
        )

    def finish(self, client):
        LOG.info("Deleting message: ({type}) {body}"
                 .format(type=self.type, body=self.body))
        client.delete_message(self.id)

    def __str__(self):
        data = {
            "body": self.body,
            "type": self.type
        }
        if self.id:
            data.update({"id": self.id})
        return json.dumps(data)


class SubredditMessage(QueueMessage):
    def __init__(self, subreddit_name, mid=None):
        LOG.info("Created new SubredditMessage: {subreddit}"
                 .format(subreddit=subreddit_name))
        self.type = constants.SUBREDDIT_MESSAGE
        self.body = subreddit_name
        self.id = mid


class PostMessage(QueueMessage):
    def __init__(self, post_link, mid=None):
        LOG.info("Created new PostMessage: {post}"
                 .format(post=post_link))
        self.type = constants.POST_MESSAGE
        self.body = post_link
        self.id = mid

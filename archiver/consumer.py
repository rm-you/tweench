import importlib
import logging

import praw

from archiver import clients
from archiver import constants
from archiver import config
from archiver import messages
from archiver import image_handling

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class Consumer(object):
    def __init__(self):
        self.conf = config.get_config()
        self.r = praw.Reddit(self.conf.REDDIT_AGENT_NAME)
        self.sqs = clients.sqs_client(self.conf.QUEUE_NAME)
        self.downloader = image_handling.DownloadHandler()
        self._type_map = {
            constants.SUBREDDIT_MESSAGE: self.store_subreddit,
            constants.POST_MESSAGE: self.store_post
        }
        persistence_module, persistence_class = (
            self.conf.PERSISTENCE_DRIVER.split(':')
        )
        persistence_module = importlib.import_module(persistence_module)
        persistence_class = getattr(persistence_module, persistence_class)
        self.persistence = persistence_class()

    def run_once(self):
        resp = self.sqs.get_message()
        if resp:
            if resp.type in self._type_map:
                LOG.info("Got message: {message}".format(message=resp))
                self._type_map[resp.type](resp.body)
                resp.finish(self.sqs)
            else:
                LOG.error("Got message of unknown type: {message}"
                          .format(message=resp))

    def store_subreddit(self, subreddit_name):
        LOG.info("Storing subreddit: {subreddit}"
                 .format(subreddit=subreddit_name))
        praw_subreddit = self.r.get_subreddit(subreddit_name)
        self.persistence.persist_subreddit(praw_subreddit)

        # posts = praw_subreddit.get_hot(limit=2)
        # posts = praw_subreddit.get_top_from_day(limit=100)
        posts = praw_subreddit.get_top_from_all(limit=10)
        for post in posts:
            m = messages.PostMessage(post.permalink)
            m.enqueue(self.sqs)

    def store_post(self, post_link):
        LOG.info("Storing post: {post}"
                 .format(post=post_link))
        praw_post = self.r.get_submission(post_link)
        self.persistence.persist_user(praw_post.author)
        self.persistence.persist_post(praw_post)

        images = self.downloader.store_images(praw_post)
        if images:
            self.persistence.persist_images(images)
        self.persistence.finalize_post(praw_post)

import logging

import praw

from archiver import clients
from archiver import config
from archiver import constants
from archiver import image_handling
from archiver import messages

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class Consumer(object):
    def __init__(self, override_queue_name=None):
        self.conf = config.get_config()
        self.r = praw.Reddit(self.conf.REDDIT_AGENT_NAME)
        self.sqs = clients.sqs_client(override_queue_name or
                                      self.conf.QUEUE_NAME)
        self.downloader = image_handling.DownloadHandler()
        self._type_map = {
            constants.MESSAGE_SUBREDDIT: self.store_subreddit,
            constants.MESSAGE_POST: self.store_post
        }
        self.persistence = clients.persistence_client()

    def run_once(self):
        resp = self.sqs.get_message()
        if resp:
            if resp.type in self._type_map:
                LOG.debug(u"Got message: {msg}"
                          .format(msg=str(resp)))
                self._type_map[resp.type](**resp.body)
                resp.finish(self.sqs)
            else:
                LOG.error(u"Got message of unknown type: {message}"
                          .format(message=resp))

    def store_subreddit(self, subreddit_name, query_type, query_num):
        LOG.info(u"Storing subreddit: {subreddit}"
                 .format(subreddit=subreddit_name))
        praw_subreddit = self.r.get_subreddit(subreddit_name)
        self.persistence.persist_subreddit(praw_subreddit)

        func = getattr(praw_subreddit, query_type)
        posts = func(limit=query_num)
        for post in posts:
            m = messages.PostMessage(post.permalink)
            m.enqueue(self.sqs)

    def store_post(self, post_link):
        LOG.info(u"Storing post: {post}".format(post=post_link))
        try:
            praw_post = self.r.get_submission(post_link)
        except praw.errors.NotFound:
            LOG.info(u"Post not found: {post}".format(post=post_link))
            return
        self.persistence.persist_user(praw_post.author)
        post_existed = self.persistence.persist_post(praw_post)
        if post_existed:
            LOG.info(u"Already stored, ignoring post: {post}"
                     .format(post=post_link))
            return

        images = self.downloader.store_images(praw_post)
        if images:
            self.persistence.persist_images(images)
        self.persistence.finalize_post(praw_post, images)

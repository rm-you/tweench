from archiver import clients
from archiver import constants
from archiver import config
from archiver import messages
from archiver import image_handling
import logging
import praw

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

    def persist_subreddit(self, praw_subreddit):
        data = {
            'id': praw_subreddit.id,
            'name': praw_subreddit.display_name,
            'title': praw_subreddit.title,
        }
        LOG.info("Persisting subreddit to DB: {subreddit}"
                 .format(subreddit=data))

    def persist_user(self, praw_user):
        data = {
            'id': praw_user.id,
            'name': praw_user.name
        }
        LOG.info("Persisting user to DB: {user}"
                 .format(user=data))

    def persist_post(self, praw_post):
        data = {
            'id': praw_post.id,
            'title': praw_post.title,
            'permalink': praw_post.permalink,
            'url': praw_post.url,
            'retrieved': False
        }
        LOG.info("Persisting post to DB: {post}"
                 .format(post=data))

    def finalize_post(self, praw_post):
        LOG.info("Marking post as retrieved: {post}"
                 .format(post=praw_post.permalink))

    def persist_images(self, images):
        LOG.info("Got {num} images, persisting them."
                 .format(num=len(images)))

    def store_subreddit(self, subreddit_name):
        LOG.info("Storing subreddit: {subreddit}"
                 .format(subreddit=subreddit_name))
        praw_subreddit = self.r.get_subreddit(subreddit_name)
        self.persist_subreddit(praw_subreddit)

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
        self.persist_user(praw_post.author)
        self.persist_post(praw_post)

        images = self.downloader.store_images(praw_post)
        if images:
            self.persist_images(images)
        self.finalize_post(praw_post)

import logging

from archiver.persistence import base as base_persistence

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class LoggingPersistence(base_persistence.Persistence):
    def __init__(self):
        LOG.info("Initialized LOGGING persistence engine.")

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

    def persist_images(self, images):
        LOG.info("Got {num} images, persisting them."
                 .format(num=len(images)))

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

    def finalize_post(self, praw_post, images):
        LOG.info("Marking post as retrieved: {post}"
                 .format(post=praw_post.permalink))

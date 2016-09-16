import abc

import six


@six.add_metaclass(abc.ABCMeta)
class Persistence(object):

    @abc.abstractmethod
    def persist_subreddit(self, praw_subreddit):
        pass

    @abc.abstractmethod
    def persist_user(self, praw_user):
        pass

    @abc.abstractmethod
    def persist_images(self, images):
        pass

    @abc.abstractmethod
    def persist_post(self, praw_post):
        pass

    @abc.abstractmethod
    def finalize_post(self, praw_post, images):
        pass

    @abc.abstractmethod
    def get_image(self, image_path):
        pass

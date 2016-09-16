from archiver.persistence import base as base_persistence


class SqlPersistence(base_persistence.Persistence):
    def persist_subreddit(self, praw_subreddit):
        raise NotImplementedError()

    def persist_user(self, praw_user):
        raise NotImplementedError()

    def persist_images(self, images):
        raise NotImplementedError()

    def persist_post(self, praw_post):
        raise NotImplementedError()

    def finalize_post(self, praw_post, images):
        raise NotImplementedError()

    def exists_image(self, image_path):
        raise NotImplementedError()

import ConfigParser


def get_config(_config={}):
    if 'config' not in _config:
        _config['config'] = Config()
    return _config['config']


class Config(object):
    def __init__(self, config_file='tweench.cfg'):
        config = ConfigParser.ConfigParser()
        config.read(config_file)

        # SQS
        self.QUEUE_NAME = config.get('sqs', 'queue_name')

        # S3
        self.IMAGE_BUCKET_NAME = config.get('s3', 'image_bucket')
        self.THUMB_BUCKET_NAME = config.get('s3', 'thumb_bucket')
        self.THUMBNAIL_SIZE = config.getint('s3', 'thumbnail_size')

        # Auth
        self.AWS_ACCESS_KEY_ID = config.get('auth', 'access_key_id')
        self.AWS_ACCESS_KEY_SECRET = config.get('auth', 'access_key_secret')
        self.AWS_REGION = config.get('auth', 'region')

        # Imgur
        self.IMGUR_CLIENT_ID = config.get('imgur', 'client_id')
        self.IMGUR_MASHAPE_KEY = config.get('imgur', 'mashape_key')

        # Reddit
        self.REDDIT_AGENT_NAME = config.get('reddit', 'agent_name')

        # Persistence
        self.PERSISTENCE_DRIVER = config.get('persistence', 'driver')

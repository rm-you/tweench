import ConfigParser

config = ConfigParser.ConfigParser()
config.read('tweench.cfg')

# SQS
QUEUE_NAME = config.get('sqs', 'queue_name')

# S3
IMAGE_BUCKET_NAME = config.get('s3', 'image_bucket')
THUMB_BUCKET_NAME = config.get('s3', 'thumb_bucket')
THUMBNAIL_SIZE = config.getint('s3', 'thumbnail_size')

# Auth
AWS_ACCESS_KEY_ID = config.get('auth', 'access_key_id')
AWS_ACCESS_KEY_SECRET = config.get('auth', 'access_key_secret')
AWS_REGION = config.get('auth', 'region')

# Imgur
IMGUR_CLIENT_ID = config.get('imgur', 'client_id')
IMGUR_MASHAPE_KEY = config.get('imgur', 'mashape_key')
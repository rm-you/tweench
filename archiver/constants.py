import ConfigParser

config = ConfigParser.ConfigParser()
config.read('tweench.cfg')

SUBREDDIT_MESSAGE = u'subreddit'
POST_MESSAGE = u'post'

QUEUE_NAME = config.get('sqs', 'queue_name')
IMAGE_BUCKET_NAME = config.get('s3', 'image_bucket')
THUMB_BUCKET_NAME = config.get('s3', 'thumb_bucket')
THUMBNAIL_SIZE = 300

AWS_ACCESS_KEY_ID = config.get('auth', 'access_key_id')
AWS_ACCESS_KEY_SECRET = config.get('auth', 'access_key_secret')
AWS_REGION = config.get('auth', 'region')

# Regexes
IMGUR_ALBUM = 'https?://(www\.|m\.)?imgur\.com/a/(.*)'
IMGUR_GALLERY = 'https?://(www\.|m\.)?imgur\.com/gallery/(.*)'
IMGUR_PAGE = 'https?://(www\.|m\.)?imgur\.com/(.*)'
IMGUR_SINGLE = 'https?://(i\.|www\.|m\.)?imgur\.com/((.*)(\..*))'
GFYCAT = 'https?://.*\.gfycat.com/(.*)'
EXTERNAL = '(https?://.*/(.*?\.(?:jpe?g|gif|png)))'

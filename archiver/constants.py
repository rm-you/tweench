# Message types
MESSAGE_SUBREDDIT = u'STORE_SUBREDDIT'
MESSAGE_POST = u'STORE_POST'

# Query types
QUERY_TOP_ALL_TIME = 'get_top_from_all'
QUERY_TOP_TODAY = 'get_top_from_day'
QUERY_HOT = 'get_hot'

# Regexes
IMGUR_ALBUM = '^https?://(?:m\.|www\.)?imgur\.com/a/([a-zA-Z0-9]+)'
IMGUR_GALLERY = '^https?://(?:m\.|www\.)?imgur\.com/gallery/([a-zA-Z0-9]+)'
IMGUR_HASHES = '^https?://(?:m\.|www\.)?imgur\.com/((?:[a-zA-Z0-9]{5,7}[&,]?)+)'
IMGUR_PAGE = 'https?://(?:www\.|m\.)?imgur\.com/(.*)'
IMGUR_SINGLE = 'https?://(?:i\.|www\.|m\.)?imgur\.com/(.*?)(?:\..*)'
GFYCAT = 'https?://.*\.gfycat.com/(.*)'
EXTERNAL = '(https?://.*/(?:.*?\.(?:jpe?g|gifv?|png)))'

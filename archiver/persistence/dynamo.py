import datetime
import time

from archiver import clients
from archiver.persistence import base as base_persistence

SUBREDDIT_TABLE = 'subreddits'
POST_TABLE = 'posts'
IMAGE_TABLE = 'images'

TABLE_DEFINITIONS = {
    SUBREDDIT_TABLE: {
        'TableName': SUBREDDIT_TABLE,
        'KeySchema': [
            {
                'AttributeName': 'name',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'name',
                'AttributeType': 'S'
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    },
    POST_TABLE: {
        'TableName': POST_TABLE,
        'KeySchema': [
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 2
        }
    },
    IMAGE_TABLE: {
        'TableName': IMAGE_TABLE,
        'KeySchema': [
            {
                'AttributeName': 'path',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'path',
                'AttributeType': 'S'
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    },
}


class DynamoPersistence(base_persistence.Persistence):
    tables = None

    def __init__(self):
        self.db = clients.get_session().resource('dynamodb')
        self.tables = {x.name: x for x in self.db.tables.all()}
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        created_tables = False
        for t in TABLE_DEFINITIONS:
            if t not in self.tables:
                self.tables[t] = self.db.create_table(**TABLE_DEFINITIONS[t])
                created_tables = True
        if created_tables:
            # DynamoDB tables take a moment to propagate (or we get 400s)
            time.sleep(10)

    def persist_subreddit(self, praw_subreddit):
        data = {
            'id': praw_subreddit.id,
            'name': praw_subreddit.display_name,
            'title': praw_subreddit.title,
        }
        sub = self.tables[SUBREDDIT_TABLE].get_item(Key={'name': praw_subreddit.display_name})
        if 'Item' not in sub:
            print("sub not found: %s" % praw_subreddit.display_name)
            self.tables[SUBREDDIT_TABLE].put_item(Item=data)

    def persist_user(self, praw_user):
        pass

    def persist_images(self, images):
        with self.tables[IMAGE_TABLE].batch_writer() as batch:
            for i in images:
                if 'path' in i:
                    batch.put_item(Item=i)

    def persist_post(self, praw_post):
        # Only check to see if the post existed already
        post = self.tables[POST_TABLE].get_item(Key={'id': praw_post.id})
        if 'Item' in post:
            return True
        return False

    def get_image(self, image_path):
        image = self.tables[IMAGE_TABLE].get_item(Key={'path': image_path})
        return image.get('Item')

    def finalize_post(self, praw_post, images):
        created = datetime.datetime.utcfromtimestamp(praw_post.created_utc)
        data = {
            'id': praw_post.id,
            'title': praw_post.title,
            'permalink': praw_post.permalink,
            'url': praw_post.url,
            'user': praw_post.author.name if praw_post.author else None,
            'images': images,
            'nsfw': praw_post.over_18,
            'created': str(created),
            'subreddit': praw_post.subreddit.display_name
        }
        self.tables[POST_TABLE].put_item(Item=data)

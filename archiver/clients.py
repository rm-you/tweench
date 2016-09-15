import json
import logging

from boto3 import session
from botocore import exceptions as boto_exceptions
import requests

from archiver import config
from archiver import constants
from archiver import messages

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

_CLIENTS = {
    'session': None,
    'sqs': {},
    's3': None
}


def sqs_client(queue):
    if queue not in _CLIENTS['sqs']:
        _CLIENTS['sqs'][queue] = SQSClient(queue)
    return _CLIENTS['sqs'][queue]


def s3_client():
    if not _CLIENTS['s3']:
        _CLIENTS['s3'] = S3Client()
    return _CLIENTS['s3']


def get_session():
    conf = config.get_config()
    if not _CLIENTS['session']:
        _CLIENTS['session'] = session.Session(
            aws_access_key_id=conf.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=conf.AWS_ACCESS_KEY_SECRET,
            region_name=conf.AWS_REGION,
        )
    return _CLIENTS['session']


class S3Client(object):
    def __init__(self):
        self.client = get_session().client('s3')

    def upload(self, bucket, path, data, extra_args=None):
        LOG.info("Uploading file to S3 ({}): {}".format(bucket, path))
        self.client.upload_fileobj(
            data, bucket, path, extra_args
        )

    def object_exists(self, bucket, path):
        try:
            self.client.head_object(Bucket=bucket, Key=path)
        except boto_exceptions.ClientError:
            return False
        LOG.info("File already exists in S3: {}".format(path))
        return True


class SQSClient(object):
    _message_types = {
        constants.SUBREDDIT_MESSAGE: messages.SubredditMessage,
        constants.POST_MESSAGE: messages.PostMessage
    }

    def __init__(self, queue_name):
        self.client = get_session().client('sqs')

        # Get the Queue URL
        response = self.client.get_queue_url(
            QueueName=queue_name
        )
        self.queue_url = response['QueueUrl']

    def send_message(self, message):
        self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=message
        )

    def get_message(self, wait=20):
        resp = self.client.receive_message(
            QueueUrl=self.queue_url,
            AttributeNames=['All'],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=wait
        )
        if resp.get('Messages'):
            m = resp.get('Messages')[0]
            body = json.loads(m['Body'])
            receipt_handle = m['ReceiptHandle']
            m_obj = self._message_types[body.get('type')](body.get('body'),
                                                          receipt_handle)
            return m_obj
        return None

    def delete_message(self, mid):
        self.client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=mid
        )


class ImgurClient(object):
    _base_url = "https://api.imgur.com"
    _album = "/3/album/{id}"
    _image = "/3/image/{id}"

    def __init__(self, client_id):
        self.client_id = client_id

    def _prepare_headers(self):
        headers = {
            'Authorization': 'Client-ID {0}'.format(self.client_id),
        }
        return headers

    def get_album(self, album_id):
        album_url = self._album.format(id=album_id)
        url = "{0}{1}".format(self._base_url, album_url)
        r = requests.get(url, headers=self._prepare_headers())
        images = r.json().get('data', {}).get('images', [])
        links = [i.get('link') for i in images if i.get('link')]
        return links

    def get_image(self, image_id):
        image_url = self._image.format(id=image_id)
        url = "{0}{1}".format(self._base_url, image_url)
        r = requests.get(url, headers=self._prepare_headers())
        link = r.json().get('data', {}).get('link')
        return link


class MashapeImgurClient(ImgurClient):
    _base_url = "https://imgur-apiv3.p.mashape.com"

    def __init__(self, client_id, mashape_key):
        super(MashapeImgurClient, self).__init__(client_id)
        self.mashape_key = mashape_key

    def _prepare_headers(self):
        headers = super(MashapeImgurClient, self)._prepare_headers()
        headers.update({'X-Mashape-Key': self.mashape_key})
        return headers

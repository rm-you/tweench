import json
from boto3 import session
from archiver import messages
from archiver import constants

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
    if not _CLIENTS['session']:
        _CLIENTS['session'] = session.Session(
            aws_access_key_id=constants.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=constants.AWS_ACCESS_KEY_SECRET,
            region_name=constants.AWS_REGION,
        )
    return _CLIENTS['session']


class S3Client(object):
    def __init__(self):
        self.client = get_session().client('s3')

    def upload(self, bucket, path, data, extra_args=None):
        self.client.upload_fileobj(
            data, bucket, path, extra_args
        )


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

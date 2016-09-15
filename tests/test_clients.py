import json
import unittest

from botocore import exceptions as boto_exceptions
import mock
import requests_mock

from archiver import clients
from archiver import constants
from archiver import messages

FAKE_QUEUE_NAME1 = 'myqueue1'
FAKE_QUEUE_NAME2 = 'myqueue2'
FAKE_MESSAGE = 'mymessage'
FAKE_MESSAGE_TYPE = constants.SUBREDDIT_MESSAGE
FAKE_RECEIPT_ID = '45678'
FAKE_WAIT_TIME = 17

FAKE_BUCKET_NAME = 'mybucket'
FAKE_PATH = 'test/path/to/object'
FAKE_DATA = b'12345'
FAKE_EXTRA_ARGS = {1: 2}

FAKE_IMGUR_CLIENT_ID = 'qwerty'
FAKE_MASHAPE_KEY = 'uiop'
FAKE_ALBUM_ID = 'asdf'
FAKE_IMAGE_ID1 = 'asdf'
FAKE_IMAGE_ID2 = 'ghjk'
FAKE_IMAGE_NAME1 = '{}.jpg'.format(FAKE_IMAGE_ID1)
FAKE_IMAGE_NAME2 = '{}.jpg'.format(FAKE_IMAGE_ID2)
FAKE_IMAGE_URL1 = 'http://i.imgur.com/{}'.format(FAKE_IMAGE_NAME1)
FAKE_IMAGE_URL2 = 'http://i.imgur.com/{}'.format(FAKE_IMAGE_NAME2)


class TestClientMethods(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('archiver.clients.config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

    @mock.patch('archiver.clients.get_session')
    def test_sqs_client(self, mock_session):
        # Get clients for FAKE_QUEUE_NAME1 twice and FAKE_QUEUE_NAME2 once
        sqs1 = clients.sqs_client(FAKE_QUEUE_NAME1)
        sqs2 = clients.sqs_client(FAKE_QUEUE_NAME1)
        sqs3 = clients.sqs_client(FAKE_QUEUE_NAME2)

        # Both FAKE_QUEUE_NAME1 clients should be the same object
        self.assertTrue(sqs1 is sqs2)
        self.assertFalse(sqs1 is sqs3)

        # The session should have two calls for clients
        mock_session().client.assert_has_calls([
            mock.call('sqs'), mock.call('sqs')
        ], any_order=True)

    @mock.patch('archiver.clients.get_session')
    def test_s3_client(self, mock_session):
        # Get two s3 clients
        s3_1 = clients.s3_client()
        s3_2 = clients.s3_client()

        # Both should be the same object
        self.assertTrue(s3_1 is s3_2)

        # The session should have only one s3 call
        mock_session().client.assert_has_calls(
            [mock.call('s3')], any_order=True)

    @mock.patch('archiver.clients.session.Session')
    def test_get_session(self, mock_boto_session):
        # Get the session twice
        session1 = clients.get_session()
        session2 = clients.get_session()

        # Both should be the same object
        self.assertTrue(session1 is session2)

        # Boto should have one session request
        config = self.mock_config.get_config()
        mock_boto_session.assert_called_with(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_ACCESS_KEY_SECRET,
            region_name=config.AWS_REGION
        )


class TestS3Client(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('archiver.clients.config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('archiver.clients.get_session')
        self.mock_session = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_client = self.mock_session().client

    def _make_s3client(self):
        s3 = clients.S3Client()
        self.mock_client.assert_called_once_with('s3')
        self.assertEqual(s3.client, self.mock_client())
        return s3

    def test_upload(self):
        s3 = self._make_s3client()

        s3.upload(FAKE_BUCKET_NAME, FAKE_PATH, FAKE_DATA)

        self.mock_client().upload_fileobj.assert_called_once_with(
            FAKE_DATA, FAKE_BUCKET_NAME, FAKE_PATH, None
        )

    def test_upload_extra_args(self):
        s3 = self._make_s3client()

        s3.upload(FAKE_BUCKET_NAME, FAKE_PATH, FAKE_DATA,
                  extra_args=FAKE_EXTRA_ARGS)

        self.mock_client().upload_fileobj.assert_called_once_with(
            FAKE_DATA, FAKE_BUCKET_NAME, FAKE_PATH, FAKE_EXTRA_ARGS
        )

    def test_object_exists_true(self):
        s3 = self._make_s3client()

        exists = s3.object_exists(FAKE_BUCKET_NAME, FAKE_PATH)

        self.mock_client().head_object.assert_called_once_with(
            Bucket=FAKE_BUCKET_NAME, Key=FAKE_PATH
        )
        self.assertTrue(exists)

    def test_object_exists_false(self):
        s3 = self._make_s3client()
        self.mock_client().head_object.side_effect = (
            boto_exceptions.ClientError(
                {'Error': {'Code': 403, 'Message': 'Forbidden'}}, 'HeadObject')
        )

        exists = s3.object_exists(FAKE_BUCKET_NAME, FAKE_PATH)

        self.mock_client().head_object.assert_called_once_with(
            Bucket=FAKE_BUCKET_NAME, Key=FAKE_PATH
        )
        self.assertFalse(exists)


class TestSQSClient(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('archiver.clients.config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('archiver.clients.get_session')
        self.mock_session = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_client = self.mock_session().client

    def _make_sqsclient(self):
        sqs = clients.SQSClient(FAKE_QUEUE_NAME1)
        self.mock_client.assert_called_once_with('sqs')
        self.assertEqual(sqs.client, self.mock_client())
        return sqs

    def test_send_message(self):
        sqs = self._make_sqsclient()

        sqs.send_message(FAKE_MESSAGE)

        self.mock_client().get_queue_url.assert_any_call(
            QueueName=FAKE_QUEUE_NAME1
        )
        self.mock_client().send_message.assert_called_once_with(
            QueueUrl=self.mock_client().get_queue_url().__getitem__(),
            MessageBody=FAKE_MESSAGE
        )

    def test_get_message(self):
        sqs = self._make_sqsclient()

        self.mock_client().receive_message.return_value = {
            'Messages': [{
                'Body': json.dumps({
                    'type': FAKE_MESSAGE_TYPE,
                    'body': FAKE_MESSAGE
                }),
                'ReceiptHandle': FAKE_RECEIPT_ID
            }]
        }

        resp = sqs.get_message(wait=FAKE_WAIT_TIME)

        self.mock_client().receive_message.assert_called_once_with(
            QueueUrl=self.mock_client().get_queue_url().__getitem__(),
            AttributeNames=['All'],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=FAKE_WAIT_TIME
        )
        self.assertIsInstance(resp, messages.SubredditMessage)
        self.assertEqual(resp.body, FAKE_MESSAGE)
        self.assertEqual(resp.type, constants.SUBREDDIT_MESSAGE)
        self.assertEqual(resp.id, FAKE_RECEIPT_ID)

    def test_get_message_timeout(self):
        sqs = self._make_sqsclient()

        self.mock_client().receive_message.return_value = {}

        resp = sqs.get_message(wait=FAKE_WAIT_TIME)

        self.assertIsNone(resp)

    def test_delete_message(self):
        sqs = self._make_sqsclient()

        sqs.delete_message(FAKE_RECEIPT_ID)

        self.mock_client().get_queue_url.assert_any_call(
            QueueName=FAKE_QUEUE_NAME1
        )
        self.mock_client().delete_message.assert_called_once_with(
            QueueUrl=self.mock_client().get_queue_url().__getitem__(),
            ReceiptHandle=FAKE_RECEIPT_ID
        )


class TestImgurClient(unittest.TestCase):
    def setUp(self):
        self.imgur_client = clients.ImgurClient(FAKE_IMGUR_CLIENT_ID)

        self.expected_headers = {
            'Authorization': 'Client-ID {0}'.format(FAKE_IMGUR_CLIENT_ID),
        }
        self.expected_album_url = "https://api.imgur.com/3/album/{id}".format(
            id=FAKE_ALBUM_ID)
        self.expected_image_url = "https://api.imgur.com/3/image/{id}".format(
            id=FAKE_IMAGE_ID1)

    def test__prepare_headers(self):
        headers = self.imgur_client._prepare_headers()

        self.assertEqual(self.expected_headers, headers)

    @requests_mock.mock()
    def test_get_album(self, mock_req):
        fake_content = {'data': {'images': [
            {'link': FAKE_IMAGE_URL1}, {'link': FAKE_IMAGE_URL2}
        ]}}
        mock_req.get(self.expected_album_url, json=fake_content)

        album = self.imgur_client.get_album(FAKE_ALBUM_ID)

        self.assertListEqual(album, [FAKE_IMAGE_URL1, FAKE_IMAGE_URL2])

    @requests_mock.mock()
    def test_get_image(self, mock_req):
        fake_content = {'data': {'link': FAKE_IMAGE_URL1}}
        mock_req.get(self.expected_image_url, json=fake_content)

        image = self.imgur_client.get_image(FAKE_IMAGE_ID1)

        self.assertEqual(image, FAKE_IMAGE_URL1)


class TestMashapeImgurClient(TestImgurClient):
    def setUp(self):
        self.imgur_client = clients.MashapeImgurClient(
            FAKE_IMGUR_CLIENT_ID, FAKE_MASHAPE_KEY)

        self.expected_headers = {
            'Authorization': 'Client-ID {0}'.format(FAKE_IMGUR_CLIENT_ID),
            'X-Mashape-Key': FAKE_MASHAPE_KEY
        }
        self.expected_album_url = (
            "https://imgur-apiv3.p.mashape.com/3/album/{id}".format(
                id=FAKE_ALBUM_ID)
        )
        self.expected_image_url = (
            "https://imgur-apiv3.p.mashape.com/3/image/{id}".format(
                id=FAKE_IMAGE_ID1)
        )

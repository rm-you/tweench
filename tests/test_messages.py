import json
import unittest

import mock

from archiver import constants
from archiver import messages
from archiver import clients

FAKE_SUBREDDIT_NAME = 'test_subreddit'
FAKE_POST_LINK = 'https://www.reddit.com/r/testsub/comments/12345/mypost/'
FAKE_MESSAGE_ID = '12345'


class TestQueueMessage(unittest.TestCase):
    def test_str(self):
        message = messages.QueueMessage()
        message.type = 2
        message.body = 3
        expected_str = json.dumps({
            "type": 2, "body": 3
        })
        self.assertEqual(str(message), expected_str)
        message.id = 1
        expected_str = json.dumps({
            "id": 1, "type": 2, "body": 3
        })
        self.assertEqual(str(message), expected_str)


class TestSubredditMessage(unittest.TestCase):
    def test_str(self):
        message = messages.SubredditMessage(FAKE_SUBREDDIT_NAME)
        expected_str = json.dumps({
            "body": FAKE_SUBREDDIT_NAME, "type": constants.SUBREDDIT_MESSAGE
        })
        self.assertEqual(str(message), expected_str)

    def test_enqueue(self):
        message = messages.SubredditMessage(FAKE_SUBREDDIT_NAME)
        mock_queue = mock.Mock(spec=clients.SQSClient)
        message.enqueue(mock_queue)
        mock_queue.send_message.assert_called_once_with(str(message))

    def test_finish(self):
        message = messages.SubredditMessage(FAKE_SUBREDDIT_NAME,
                                            mid=FAKE_MESSAGE_ID)
        mock_queue = mock.Mock(spec=clients.SQSClient)
        message.finish(mock_queue)
        mock_queue.delete_message.assert_called_once_with(message.id)

    def test_finish_no_id(self):
        message = messages.SubredditMessage(FAKE_SUBREDDIT_NAME)
        mock_queue = mock.Mock(spec=clients.SQSClient)
        self.assertRaises(AttributeError, message.finish, mock_queue)


class TestPostMessage(unittest.TestCase):
    def test_str(self):
        message = messages.PostMessage(FAKE_POST_LINK)
        expected_str = json.dumps({
            "body": FAKE_POST_LINK, "type": constants.POST_MESSAGE
        })
        self.assertEqual(str(message), expected_str)

    def test_enqueue(self):
        message = messages.PostMessage(FAKE_POST_LINK)
        mock_queue = mock.Mock(spec=clients.SQSClient)
        message.enqueue(mock_queue)
        mock_queue.send_message.assert_called_once_with(str(message))

    def test_finish(self):
        message = messages.PostMessage(FAKE_POST_LINK,
                                       mid=FAKE_MESSAGE_ID)
        mock_queue = mock.Mock(spec=clients.SQSClient)
        message.finish(mock_queue)
        mock_queue.delete_message.assert_called_once_with(message.id)

    def test_finish_no_id(self):
        message = messages.PostMessage(FAKE_POST_LINK)
        mock_queue = mock.Mock(spec=clients.SQSClient)
        self.assertRaises(AttributeError, message.finish, mock_queue)

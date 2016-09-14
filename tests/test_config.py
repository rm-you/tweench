import mock
import unittest

from archiver import config


class TestConfig(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch('archiver.config.ConfigParser.ConfigParser')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_config_singleton(self):
        conf1 = config.get_config()
        conf2 = config.get_config()
        self.assertTrue(conf1 is conf2)

    def test_required_attributes(self):
        conf = config.get_config()

        self.assertIn('QUEUE_NAME', conf.__dict__)
        self.assertIn('IMAGE_BUCKET_NAME', conf.__dict__)
        self.assertIn('THUMB_BUCKET_NAME', conf.__dict__)
        self.assertIn('THUMBNAIL_SIZE', conf.__dict__)
        self.assertIn('AWS_ACCESS_KEY_ID', conf.__dict__)
        self.assertIn('AWS_ACCESS_KEY_SECRET', conf.__dict__)
        self.assertIn('AWS_REGION', conf.__dict__)
        self.assertIn('IMGUR_CLIENT_ID', conf.__dict__)
        self.assertIn('IMGUR_MASHAPE_KEY', conf.__dict__)
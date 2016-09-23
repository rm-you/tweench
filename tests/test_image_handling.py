import hashlib

import mock
import requests_mock
from requests import structures
import unittest

from archiver import image_handling

FAKE_SUBREDDIT_NAME = 'test_subreddit'
FAKE_USERNAME = 'test_user'
FAKE_POST_ID = 'post1'

FAKE_IMAGE_ID1 = 'asdf'
FAKE_IMAGE_ID2 = 'ghjk'
FAKE_IMAGE_HASHES = '{},{}'.format(FAKE_IMAGE_ID1, FAKE_IMAGE_ID2)
FAKE_IMAGE_NAME1 = '{}.jpg'.format(FAKE_IMAGE_ID1)
FAKE_IMAGE_NAME2 = '{}.jpg'.format(FAKE_IMAGE_ID2)
FAKE_IMAGE_URL1 = 'http://i.imgur.com/{}'.format(FAKE_IMAGE_NAME1)
FAKE_IMAGE_URL2 = 'http://i.imgur.com/{}'.format(FAKE_IMAGE_NAME2)
FAKE_IMAGE_URL1_MD5 = hashlib.md5(FAKE_IMAGE_URL1).hexdigest()
FAKE_IMAGE_URL2_MD5 = hashlib.md5(FAKE_IMAGE_URL2).hexdigest()
FAKE_IMAGE_PATH1 = '{}/{}'.format(FAKE_IMAGE_URL1_MD5, FAKE_IMAGE_NAME1)
FAKE_IMAGE_PATH2 = '{}/{}'.format(FAKE_IMAGE_URL2_MD5, FAKE_IMAGE_NAME2)
FAKE_IMAGE_DATA1 = b'12345'
FAKE_IMAGE_DATA2 = b'67890'

FAKE_GFY_ID = 'OctopusCluster'
FAKE_GFY_WEBM_NAME = '{}.webm'.format(FAKE_GFY_ID)
FAKE_GFY_WEBM = 'https://fat.gfycat.com/{}'.format(FAKE_GFY_WEBM_NAME)
FAKE_GFY_THUMB = 'https://thumbs.gfycat.com/{}-small.gif'.format(FAKE_GFY_ID)
FAKE_GFY_WEBM_MD5 = hashlib.md5(FAKE_GFY_WEBM).hexdigest()
FAKE_GFY_PATH = '{}/{}'.format(FAKE_GFY_WEBM_MD5, FAKE_GFY_WEBM_NAME)
FAKE_CONTENT_TYPE_WEBM = "video/webm"
FAKE_CONTENT_TYPE_GIF = "image/gif"
FAKE_GFY_IMAGE_WIDTH = 1024
FAKE_GFY_IMAGE_HEIGHT = 768

FAKE_CLIENT_ID = 'myclient'
FAKE_MASHAPE_KEY = 'mykey'
FAKE_THUMBNAIL_SIZE = 300

FAKE_IMAGE_BUCKET_NAME = 'images'
FAKE_THUMB_BUCKET_NAME = 'images-300'
FAKE_IMAGE_FORMAT = 'jpg'
FAKE_CONTENT_TYPE = {'ContentType': "image/{}".format(FAKE_IMAGE_FORMAT)}


class TestImage(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('archiver.config.get_config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('archiver.clients.s3_client')
        self.mock_s3 = patcher.start()
        self.addCleanup(patcher.stop)

        self.pil_patcher = mock.patch('archiver.image_handling.PILImage')
        self.mock_pil = self.pil_patcher.start()
        self.addCleanup(self.pil_patcher.stop)

        patcher = mock.patch('archiver.image_handling.io.BytesIO')
        self.mock_bytesio = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_config().IMAGE_BUCKET_NAME = FAKE_IMAGE_BUCKET_NAME
        self.mock_config().THUMB_BUCKET_NAME = FAKE_THUMB_BUCKET_NAME

        self.mock_pil.open().format = FAKE_IMAGE_FORMAT
        self.mock_pil.open.reset_mock()

    def _make_image(self, path, data, thumb_data=None):
        # Make the image
        if thumb_data:
            image = image_handling.Image(path, data, thumb_data)
        else:
            image = image_handling.Image(path, data)

        # PIL object created with our BytesIO data
        self.mock_pil.open.assert_called_once_with(self.mock_bytesio())
        self.mock_bytesio.reset_mock()

        return image

    def test_bad_image_data(self):
        self.pil_patcher.stop()
        image = image_handling.Image(FAKE_IMAGE_PATH1, FAKE_IMAGE_DATA1)
        self.pil_patcher.start()

        colors = image.get_colors()
        dimensions = image.get_dimensions()

        self.assertIsNone(colors)
        self.assertIsNone(dimensions)

    def test_upload(self):
        # Make our image (and run tests for it)
        image = self._make_image(FAKE_IMAGE_PATH1, FAKE_IMAGE_DATA1)

        # Call upload
        image.upload()

        # BytesIO is created with our image data, and S3 is called with it
        self.mock_bytesio.assert_has_calls([
            mock.call(FAKE_IMAGE_DATA1)
        ])
        self.mock_s3().upload.assert_called_once_with(
            FAKE_IMAGE_BUCKET_NAME,
            FAKE_IMAGE_PATH1,
            self.mock_bytesio(),
            FAKE_CONTENT_TYPE
        )

    def test_upload_thumbnail(self):
        # Make our image (and run tests for it)
        image = self._make_image(FAKE_IMAGE_PATH1, FAKE_IMAGE_DATA1)

        # Image size of 800x600 should make a 400x300 or 300x225
        self.mock_pil.open().size = (600, 800)

        # Call upload_thumbnail using width
        image.upload_thumbnail(width=FAKE_THUMBNAIL_SIZE)

        # The main image object is resized and then saved
        self.mock_pil.open().resize.assert_called_once_with(
            (300, 400),
            self.mock_pil.ANTIALIAS
        )
        self.mock_pil.open().resize().save.assert_called_once_with(
            self.mock_bytesio(), FAKE_IMAGE_FORMAT
        )
        self.mock_pil.open().resize.reset_mock()

        # S3 is called with it
        self.mock_s3().upload.assert_called_once_with(
            FAKE_THUMB_BUCKET_NAME,
            FAKE_IMAGE_PATH1,
            self.mock_bytesio(),
            FAKE_CONTENT_TYPE
        )
        self.mock_s3().upload.reset_mock()

        # Call upload_thumbnail using height
        image.upload_thumbnail(height=FAKE_THUMBNAIL_SIZE)

        # The main image object is resized and then saved
        self.mock_pil.open().resize.assert_called_once_with(
            (225, 300),
            self.mock_pil.ANTIALIAS
        )
        self.mock_pil.open().resize().save.assert_called_once_with(
            self.mock_bytesio(), FAKE_IMAGE_FORMAT
        )

        # S3 is called with it
        self.mock_s3().upload.assert_called_once_with(
            FAKE_THUMB_BUCKET_NAME,
            FAKE_IMAGE_PATH1,
            self.mock_bytesio(),
            FAKE_CONTENT_TYPE
        )

    def test_upload_thumbnail_with_data(self):
        # Make our image (and run tests for it)
        image = self._make_image(path=FAKE_IMAGE_PATH1, data=FAKE_IMAGE_DATA1,
                                 thumb_data=FAKE_IMAGE_DATA2)

        # Call upload_thumbnail
        image.upload_thumbnail()

        # S3 is called with it
        self.mock_s3().upload.assert_called_once_with(
            FAKE_THUMB_BUCKET_NAME,
            FAKE_IMAGE_PATH1,
            self.mock_bytesio(),
            FAKE_CONTENT_TYPE
        )

    def test_upload_thumbnail_no_size(self):
        # Make our image (and run tests for it)
        image = self._make_image(FAKE_IMAGE_PATH1, FAKE_IMAGE_DATA1)

        # Calling upload_thumbnail should fail
        self.assertRaises(ArithmeticError, image.upload_thumbnail)

    @mock.patch('archiver.image_handling.colorific')
    def test_get_colors(self, mock_colorific):
        fake_color = mock.Mock()
        fake_color.prominence = 0.5
        mock_colorific.extract_colors().colors = [fake_color]
        # Make our image (and run tests for it)
        image = self._make_image(FAKE_IMAGE_PATH1, FAKE_IMAGE_DATA1)

        # Call get_colors
        colors = image.get_colors()

        # Color extraction is called on our PIL object, and colors returned
        mock_colorific.extract_colors.called_once_with(self.mock_pil)
        self.assertEqual(colors, [{
            'prominence': 50, 'value': mock_colorific.rgb_to_hex()
        }])

    @mock.patch('archiver.image_handling.colorific')
    def test_get_colors_error(self, mock_colorific):
        mock_colorific.extract_colors.side_effect = ValueError
        # Make our image (and run tests for it)
        image = self._make_image(FAKE_IMAGE_PATH1, FAKE_IMAGE_DATA1)

        # Call get_colors
        colors = image.get_colors()

        # colors is None because extraction failed
        self.assertIsNone(colors)

    def test_get_dimensions(self):
        # Make our image (and run tests for it)
        image = self._make_image(FAKE_IMAGE_PATH1, FAKE_IMAGE_DATA1)

        # Set PIL object size
        self.mock_pil.open().size = (600, 800)

        # Call get_dimensions
        dimensions = image.get_dimensions()

        # The dimensions of the PIL object are returned
        self.assertEqual(dimensions, {'height': 600, 'width': 800})


class TestDownloadHandler(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('archiver.config.get_config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('archiver.clients.s3_client')
        self.mock_s3 = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('archiver.clients.persistence_client')
        self.mock_persistence = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('archiver.clients.MashapeImgurClient')
        self.mock_imgur = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('archiver.image_handling.gfycat.GfycatClient')
        self.mock_gfycat = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_config().IMGUR_CLIENT_ID = FAKE_CLIENT_ID
        self.mock_config().IMGUR_MASHAPE_KEY = FAKE_MASHAPE_KEY
        self.mock_config().THUMBNAIL_SIZE = FAKE_THUMBNAIL_SIZE
        self.mock_config().IMAGE_BUCKET_NAME = FAKE_IMAGE_BUCKET_NAME

        self.mock_s3().object_exists.return_value = False

        self.dh = image_handling.DownloadHandler()

    @mock.patch('archiver.clients.ImgurClient')
    def test_download_handler_no_mashape_key(self, mock_imgur):
        # Remove the mashape key from config
        self.mock_config().IMGUR_MASHAPE_KEY = None

        # Create a DownloadHandler
        image_handling.DownloadHandler()

        # ImgurClient is used
        mock_imgur.assert_called_once_with(FAKE_CLIENT_ID)

    @mock.patch('archiver.image_handling.Image')
    @requests_mock.mock()
    def test__download_one_imgur_object_exists(self, mock_image, mock_req):
        img1_ret = {
            'path': FAKE_IMAGE_PATH1,
            'url': FAKE_IMAGE_URL1,
            'dimensions': mock_image().get_dimensions(),
            'colors': mock_image().get_colors()
        }
        self.mock_persistence().get_image.return_value = img1_ret
        self.mock_s3().object_exists.return_value = True
        image = self.dh._download_one_imgur(FAKE_IMAGE_URL1)

        self.assertEqual(mock_req.call_count, 0)
        self.assertEqual(image, img1_ret)

    @mock.patch.object(image_handling.DownloadHandler, '_single')
    def test_store_images(self, mock_single):
        # Make a new DownloadHandler so it will use the _single mock
        dh = image_handling.DownloadHandler()

        # Set up a fake post object using an imgur "single image" URL
        praw_post = mock.MagicMock()
        praw_post.url = FAKE_IMAGE_URL1
        praw_post.subreddit.display_name = FAKE_SUBREDDIT_NAME
        praw_post.author.name = FAKE_USERNAME
        praw_post.id = FAKE_POST_ID

        # _single returns a list with one Image
        image_mock = mock.Mock()
        mock_single.return_value = [image_mock]

        # Call store_images
        images = dh.store_images(praw_post)

        # _single is called once because the regex matches
        mock_single.assert_called_once_with(FAKE_IMAGE_ID1)
        self.assertListEqual(images, [image_mock])

    @mock.patch('archiver.image_handling.Image')
    @requests_mock.mock()
    def test__single(self, mock_image, mock_req):
        # Imgur API should return our fake image URL
        self.mock_imgur().get_image.return_value = FAKE_IMAGE_URL1

        # Requests should have one GET for our fake image URL
        mock_req.get(FAKE_IMAGE_URL1, content=FAKE_IMAGE_DATA1)

        # Call _single
        images = self.dh._single(FAKE_IMAGE_ID1)

        # Imgur API called once with FAKE_IMAGE_ID
        self.mock_imgur().get_image.assert_called_once_with(FAKE_IMAGE_ID1)

        # Downloaded the correct image URL with requests
        self.assertEqual(mock_req.call_count, 1)
        self.assertEqual(mock_req.request_history[0].url, FAKE_IMAGE_URL1)

        # Image object was created
        mock_image.assert_called_once_with(
            path=FAKE_IMAGE_PATH1, data=FAKE_IMAGE_DATA1, content_type=None,
            thumb_content_type=None, thumb_data=None)

        # Image and Thumbnail were uploaded
        mock_image().upload.assert_called_once()
        mock_image().upload_thumbnail.assert_called_once_with(
            FAKE_THUMBNAIL_SIZE)

        # Returned image list is the path/url of our image
        img_ret = {
            'path': FAKE_IMAGE_PATH1,
            'url': FAKE_IMAGE_URL1,
            'dimensions': mock_image().get_dimensions(),
            'colors': mock_image().get_colors()
        }
        self.assertListEqual(images, [img_ret])

    @mock.patch('archiver.image_handling.Image')
    @requests_mock.mock()
    def test__album(self, mock_image, mock_req):
        # Imgur API should return our fake image URLs
        self.mock_imgur().get_album.return_value = [
            FAKE_IMAGE_URL1, FAKE_IMAGE_URL2]

        # Requests should have one GET for each fake image URL
        mock_req.get(FAKE_IMAGE_URL1, content=FAKE_IMAGE_DATA1)
        mock_req.get(FAKE_IMAGE_URL2, content=FAKE_IMAGE_DATA2)

        # Call _album
        images = self.dh._album(FAKE_IMAGE_ID1)

        # Imgur API called once with FAKE_IMAGE_ID
        self.mock_imgur().get_album.assert_called_once_with(FAKE_IMAGE_ID1)

        # Downloaded the correct image URLs with requests
        self.assertEqual(mock_req.call_count, 2)
        self.assertListEqual(
            [mock_req.request_history[0].url, mock_req.request_history[1].url],
            [FAKE_IMAGE_URL1, FAKE_IMAGE_URL2]
        )

        # Image objects were created
        mock_image.assert_has_calls([
            mock.call(path=FAKE_IMAGE_PATH1, data=FAKE_IMAGE_DATA1,
                      content_type=None, thumb_content_type=None,
                      thumb_data=None),
            mock.call(path=FAKE_IMAGE_PATH2, data=FAKE_IMAGE_DATA2,
                      content_type=None, thumb_content_type=None,
                      thumb_data=None)
        ], any_order=True)

        # Image and Thumbnail were uploaded
        self.assertEqual(mock_image().upload.call_count, 2)
        self.assertEqual(mock_image().upload_thumbnail.call_count, 2)
        mock_image().upload.assert_has_calls([
            mock.call(),
            mock.call()
        ])
        mock_image().upload_thumbnail.assert_has_calls([
            mock.call(FAKE_THUMBNAIL_SIZE),
            mock.call(FAKE_THUMBNAIL_SIZE)
        ])

        # Returned image list is the path/url of the two images
        img1_ret = {
            'path': FAKE_IMAGE_PATH1,
            'url': FAKE_IMAGE_URL1,
            'dimensions': mock_image().get_dimensions(),
            'colors': mock_image().get_colors()
        }
        img2_ret = {
            'path': FAKE_IMAGE_PATH2,
            'url': FAKE_IMAGE_URL2,
            'dimensions': mock_image().get_dimensions(),
            'colors': mock_image().get_colors()
        }
        self.assertListEqual(images, [img1_ret, img2_ret])

    @mock.patch('archiver.image_handling.Image')
    @requests_mock.mock()
    def test__hashes(self, mock_image, mock_req):
        # Imgur API should return our fake image URL
        self.mock_imgur().get_image.side_effect = [
            FAKE_IMAGE_URL1, FAKE_IMAGE_URL2]

        # Requests should have one GET for each fake image URL
        mock_req.get(FAKE_IMAGE_URL1, content=FAKE_IMAGE_DATA1)
        mock_req.get(FAKE_IMAGE_URL2, content=FAKE_IMAGE_DATA2)

        # Call _hashes
        images = self.dh._hashes(FAKE_IMAGE_HASHES)

        # Imgur API called once with each FAKE_IMAGE_ID
        self.mock_imgur().get_image.assert_has_calls([
            mock.call(FAKE_IMAGE_ID1),
            mock.call(FAKE_IMAGE_ID2)
        ])

        # Downloaded the correct image URLs with requests
        self.assertEqual(mock_req.call_count, 2)
        self.assertListEqual(
            [mock_req.request_history[0].url, mock_req.request_history[1].url],
            [FAKE_IMAGE_URL1, FAKE_IMAGE_URL2]
        )

        # Image objects were created
        mock_image.assert_has_calls([
            mock.call(path=FAKE_IMAGE_PATH1, data=FAKE_IMAGE_DATA1,
                      content_type=None, thumb_content_type=None,
                      thumb_data=None),
            mock.call(path=FAKE_IMAGE_PATH2, data=FAKE_IMAGE_DATA2,
                      content_type=None, thumb_content_type=None,
                      thumb_data=None)
        ], any_order=True)

        # Image and Thumbnail were uploaded
        self.assertEqual(mock_image().upload.call_count, 2)
        self.assertEqual(mock_image().upload_thumbnail.call_count, 2)
        mock_image().upload.assert_has_calls([
            mock.call(),
            mock.call()
        ])
        mock_image().upload_thumbnail.assert_has_calls([
            mock.call(FAKE_THUMBNAIL_SIZE),
            mock.call(FAKE_THUMBNAIL_SIZE)
        ])

        # Returned image list is the path/url of the two images
        img1_ret = {
            'path': FAKE_IMAGE_PATH1,
            'url': FAKE_IMAGE_URL1,
            'dimensions': mock_image().get_dimensions(),
            'colors': mock_image().get_colors()
        }
        img2_ret = {
            'path': FAKE_IMAGE_PATH2,
            'url': FAKE_IMAGE_URL2,
            'dimensions': mock_image().get_dimensions(),
            'colors': mock_image().get_colors()
        }
        self.assertListEqual(images, [img1_ret, img2_ret])

    @mock.patch('archiver.image_handling.Image')
    @requests_mock.mock()
    def test__external(self, mock_image, mock_req):
        # Requests should have one GET for our fake image URL
        head = structures.CaseInsensitiveDict({'Content-Type': "image/jpeg"})
        mock_req.get(FAKE_IMAGE_URL1, content=FAKE_IMAGE_DATA1, headers=head)

        # Call _external
        images = self.dh._external(FAKE_IMAGE_URL1)

        # Downloaded the correct image URL with requests
        self.assertEqual(mock_req.call_count, 1)
        self.assertEqual(mock_req.request_history[0].url, FAKE_IMAGE_URL1)

        # Image object was created
        mock_image.assert_called_once_with(
            path=FAKE_IMAGE_PATH1, data=FAKE_IMAGE_DATA1,
            content_type=None, thumb_content_type=None, thumb_data=None)

        # Image and Thumbnail were uploaded
        mock_image().upload.assert_called_once()
        mock_image().upload_thumbnail.assert_called_once_with(
            FAKE_THUMBNAIL_SIZE)

        # Returned image list is the path/url of our image
        img_ret = {'path': FAKE_IMAGE_PATH1, 'url': FAKE_IMAGE_URL1}
        self.assertListEqual(images, [img_ret])

    @mock.patch('archiver.image_handling.Image')
    @requests_mock.mock()
    def test__gfycat(self, mock_image, mock_req):
        # GfycatClient should return a dict with gfyItem
        self.mock_gfycat().query_gfy.return_value = {
            'gfyItem': {
                'webmUrl': FAKE_GFY_WEBM,
                'max2mbGif': FAKE_GFY_THUMB,
                'width': FAKE_GFY_IMAGE_WIDTH,
                'height': FAKE_GFY_IMAGE_HEIGHT
            }
        }

        # Requests should have one GET for each fake image URL
        head1 = structures.CaseInsensitiveDict({'Content-Type': "video/webm"})
        head2 = structures.CaseInsensitiveDict({'Content-Type': "image/gif"})
        mock_req.get(FAKE_GFY_WEBM, content=FAKE_IMAGE_DATA1, headers=head1)
        mock_req.get(FAKE_GFY_THUMB, content=FAKE_IMAGE_DATA2, headers=head2)

        # Call _gfycat
        images = self.dh._gfycat(FAKE_GFY_ID)

        # Downloaded the correct image URLs with requests
        self.assertEqual(mock_req.call_count, 2)
        self.assertListEqual(
            [mock_req.request_history[0].url, mock_req.request_history[1].url],
            [FAKE_GFY_WEBM, FAKE_GFY_THUMB]
        )

        # Image objects were created
        mock_image.assert_called_once_with(
            path=FAKE_GFY_PATH,
            data=FAKE_IMAGE_DATA1,
            thumb_data=FAKE_IMAGE_DATA2,
            content_type=FAKE_CONTENT_TYPE_WEBM,
            thumb_content_type=FAKE_CONTENT_TYPE_GIF
        )

        # Image and Thumbnail were uploaded
        mock_image().upload.assert_called_once()
        mock_image().upload_thumbnail.assert_called_once()

        # Returned image list is the path/url of our image
        img_ret = {
            'path': FAKE_GFY_PATH,
            'url': FAKE_GFY_WEBM,
            'dimensions': {
                'height': FAKE_GFY_IMAGE_HEIGHT,
                'width': FAKE_GFY_IMAGE_WIDTH
                }
        }
        self.assertListEqual(images, [img_ret])

import collections
import hashlib
import io
import logging
import re

import colorific
from gfycat import client as gfycat
from PIL import Image as PILImage
import requests

from archiver import clients
from archiver import config
from archiver import constants


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class DownloadHandler(object):
    def __init__(self):
        self.conf = config.get_config()
        self.s3 = clients.s3_client()
        self._regexes = collections.OrderedDict([
            (re.compile(constants.IMGUR_ALBUM, re.IGNORECASE), self._album),
            (re.compile(constants.IMGUR_GALLERY, re.IGNORECASE), self._album),
            (re.compile(constants.IMGUR_HASHES, re.IGNORECASE), self._hashes),
            (re.compile(constants.IMGUR_PAGE, re.IGNORECASE), self._single),
            (re.compile(constants.IMGUR_SINGLE, re.IGNORECASE), self._single),
            (re.compile(constants.GFYCAT, re.IGNORECASE), self._gfycat),
            (re.compile(constants.EXTERNAL, re.IGNORECASE), self._external)
        ])

        if self.conf.IMGUR_MASHAPE_KEY:
            self.imgur = clients.MashapeImgurClient(
                client_id=self.conf.IMGUR_CLIENT_ID,
                mashape_key=self.conf.IMGUR_MASHAPE_KEY
            )
        else:
            self.imgur = clients.ImgurClient(self.conf.IMGUR_CLIENT_ID)

        self.gfycat = gfycat.GfycatClient()

    def store_images(self, praw_post):
        LOG.info("Determining type of image URL: {url}"
                 .format(url=praw_post.url))
        images = []
        for regex in self._regexes:
            m = regex.match(praw_post.url)
            if m:
                images.extend(self._regexes[regex](
                    *m.groups()
                ))
                break
        return images

    def _single(self, image_id):
        LOG.info("Single imgur page detected: {page}".format(page=image_id))
        image_url = self.imgur.get_image(image_id)
        image = self._download_one_imgur(image_url)
        return [image]

    def _album(self, album_id):
        LOG.info("Album detected: {album_id}".format(album_id=album_id))
        image_urls = self.imgur.get_album(album_id)
        images = [self._download_one_imgur(url)
                  for url in image_urls]
        return images

    def _hashes(self, hashes):
        hashes = hashes.strip(',').split(',')
        LOG.info("Image hashes detected: {hashes}".format(hashes=hashes))
        image_urls = [self.imgur.get_image(image_id) for image_id in hashes]
        images = [self._download_one_imgur(url) for url in image_urls]
        return images

    def _download_one_imgur(self, url):
        name = url.split('/')[-1]
        path = "{hash}/{name}".format(hash=hashlib.md5(url).hexdigest(),
                                      name=name)
        if not self.s3.object_exists(self.conf.IMAGE_BUCKET_NAME, path):
            LOG.info("Downloading '{path}': {url}".format(path=path, url=url))
            r = requests.get(url, stream=False)
            image = self._handle_image_data(r.content, path)
            return {
                'url': url,
                'path': path,
                'dimensions': image.get_dimensions(),
                'colors': image.get_colors()
            }

    def _gfycat(self, gfy_id):
        LOG.info("Gfycat detected: {gfy_id}".format(gfy_id=gfy_id))
        gfy_data = self.gfycat.query_gfy(gfy_id)
        if gfy_data and 'gfyItem' in gfy_data:
            url = gfy_data['gfyItem']['webmUrl']
            r1 = requests.get(url, stream=False)

            thumb_url = (gfy_data['gfyItem'].get('max2mbGif') or
                         gfy_data['gfyItem'].get('max5mbGif'))
            r2 = requests.get(thumb_url, stream=False)

            name = url.split('/')[-1]
            path = "{hash}/{name}".format(hash=hashlib.md5(url).hexdigest(),
                                          name=name)
            self._handle_image_data(
                data=r1.content, thumb_data=r2.content, path=path)
            return [{
                'url': url,
                'path': path,
                'dimensions': (gfy_data['gfyItem']['height'],
                               gfy_data['gfyItem']['width']),
            }]

    def _external(self, url):
        LOG.info("Generic image URL detected: {url}".format(url=url))
        name = url.split('/')[-1]
        path = "{hash}/{name}".format(hash=hashlib.md5(url).hexdigest(),
                                      name=name)
        if not self.s3.object_exists(self.conf.IMAGE_BUCKET_NAME, path):
            r = requests.get(url, stream=False)
            self._handle_image_data(r.content, path)
        return [{'url': url, 'path': path}]

    def _handle_image_data(self, data, path, thumb_data=None):
        image = Image(path=path, data=data, thumb_data=thumb_data)
        image.upload()
        image.upload_thumbnail(self.conf.THUMBNAIL_SIZE)
        return image


class Image(object):
    def __init__(self, path, data, thumb_data=None, content_type=None):
        self.conf = config.get_config()
        self.s3 = clients.s3_client()
        self.path = path
        self.data = data
        self.thumb_data = thumb_data
        io_data = io.BytesIO(self.data)
        try:
            self.pi = PILImage.open(io_data)
            self.type = content_type or self.pi.format
        except:
            self.pi = None
            self.type = content_type

    def upload(self):
        io_data = io.BytesIO(self.data)
        self.s3.upload(self.conf.IMAGE_BUCKET_NAME, self.path, io_data,
                       {"ContentType": "image/{}".format(self.type.lower())})

    def upload_thumbnail(self, width=None, height=None):
        if self.thumb_data:
            thumb_data = io.BytesIO(self.thumb_data)
        else:
            if (not width and not height) or (width and height):
                raise ArithmeticError("Must supply either width or height!")
            thumb_data = self._thumbnail(width, height)
        self.s3.upload(self.conf.THUMB_BUCKET_NAME, self.path, thumb_data,
                       {"ContentType": "image/{}".format(self.type.lower())})

    def _thumbnail(self, width=None, height=None):
        LOG.info("Thumbnailing data at ({} x {})".format(width, height))
        if width:
            wpercent = (width / float(self.pi.size[0]))
            height = int((float(self.pi.size[1]) * float(wpercent)))
        else:
            hpercent = (height / float(self.pi.size[1]))
            width = int((float(self.pi.size[0]) * float(hpercent)))

        thumb = self.pi.resize((width, height), PILImage.ANTIALIAS)
        thumb_bytes = io.BytesIO()
        thumb.save(thumb_bytes, self.type)
        thumb_bytes.seek(0)
        return thumb_bytes

    def get_colors(self):
        if self.pi:
            LOG.info("Analyzing color data for image...")
            return colorific.extract_colors(self.pi).colors

        LOG.info("Can't analyze colors, no image data.")

    def get_dimensions(self):
        if self.pi:
            LOG.info("Calculating dimensions for image...")
            return self.pi.size

        LOG.info("Can't calculate dimensions, no image data.")

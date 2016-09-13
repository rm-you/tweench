import requests
import colorific
from PIL import Image as PILImage
import io
from archiver import constants
from archiver import config
from archiver import clients
import re
import logging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class DownloadHandler(object):
    def __init__(self):
        self._regexes = {
            re.compile(constants.IMGUR_ALBUM, re.IGNORECASE): self._album,
            re.compile(constants.IMGUR_PAGE, re.IGNORECASE): self._single,
            re.compile(constants.IMGUR_SINGLE, re.IGNORECASE): self._single,
            re.compile(constants.GFYCAT, re.IGNORECASE): self._gfycat,
            re.compile(constants.EXTERNAL, re.IGNORECASE): self._external,
        }
        if config.IMGUR_MASHAPE_KEY:
            self.imgur = clients.MashapeImgurClient(
                client_id=config.IMGUR_CLIENT_ID,
                mashape_key=config.IMGUR_MASHAPE_KEY
            )
        else:
            self.imgur = clients.ImgurClient(config.IMGUR_CLIENT_ID)

    def store_images(self, praw_post):
        LOG.info("Determining type of image URL: {url}"
                 .format(url=praw_post.url))
        path = "{subreddit}/{user_name}/{post_id}".format(
            subreddit=praw_post.subreddit.display_name,
            user_name=praw_post.redditor.name,
            post_id=praw_post.id
        )
        images = []
        for regex in self._regexes.iterkeys():
            m = regex.match(praw_post.url)
            if m:
                images = self._regexes[regex](
                    *m.groups(), base_path=path
                )
                break
        return images

    def _album(self, album_id, base_path=''):
        LOG.info("Album detected: {album_id}".format(album_id=album_id))
        image_urls = self.imgur.get_album(album_id)
        images = [
            self._download_one_imgur(
                url=url, name=url.split('/')[-1], base_path=base_path
            )
            for url in image_urls
        ]
        return images

    def _single(self, image_id, base_path=''):
        LOG.info("Single imgur page detected: {page}".format(page=image_id))
        image_url = self.imgur.get_image(image_id)
        image = self._download_one_imgur(
            url=image_url, name=image_url.split('/')[-1], base_path=base_path
        )
        return image

    def _download_one_imgur(self, url, name, base_path):
        path = "{base}/{name}".format(base=base_path, name=name)
        LOG.info("--> Downloading '{path}': {url}".format(path=path, url=url))
        r = requests.get(url, stream=False)
        return self._handle_image_data(r.content, path)

    def _gfycat(self, gfy_id, base_path=''):
        LOG.info("Gfycat detected: {gfy_id}".format(gfy_id=gfy_id))

    def _external(self, url, name, base_path=''):
        LOG.info("Generic image URL detected: {url}".format(url=url))
        r = requests.get(url, stream=False)
        path = "{base}/{name}".format(base=base_path, name=name)
        return [self._handle_image_data(r.content, path)]

    def _handle_image_data(self, data, path):
        image = Image(path=path, data=data)
        image.upload()
        image.upload_thumbnail(config.THUMBNAIL_SIZE)
        return image


class Image(object):
    def __init__(self, path, data):
        self.s3 = clients.s3_client()
        self.path = path
        self.data = data
        io_data = io.BytesIO(self.data)
        self.pi = PILImage.open(io_data)
        self.type = self.pi.format

    def upload(self):
        io_data = io.BytesIO(self.data)
        self.s3.upload(config.IMAGE_BUCKET_NAME, self.path, io_data,
                       {"ContentType": "image/{}".format(self.type.lower())})

    def upload_thumbnail(self, width=None, height=None):
        if (not width and not height) or (width and height):
            raise Exception("Must supply either width or height!")
        thumb_data = self._thumbnail(width, height)
        self.s3.upload(config.THUMB_BUCKET_NAME, self.path, thumb_data,
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
        LOG.info("Analyzing color data for image...")
        color_data = colorific.extract_colors(self.pi)
        return color_data.colors

    def get_dimensions(self):
        LOG.info("Calculating dimensions for image...")
        return self.pi.size


class Gfy(Image):
    def _thumbnail(self, width=None, height=None):
        LOG.info("Fetching pre-made Gfycat thumbnail...")
        return self.data  # TODO

    def get_colors(self):
        LOG.info("Analyzing color data for Gfy...")
        return []  # TODO

    def get_dimensions(self):
        LOG.info("Calculating dimensions for Gfy...")
        return 0, 0  # TODO

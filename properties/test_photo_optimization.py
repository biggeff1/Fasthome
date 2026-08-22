from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from PIL import Image

from .photo_optimization import _compress


class PhotoOptimizationTests(SimpleTestCase):
    def test_large_image_is_compressed_to_webp(self):
        source = BytesIO()
        Image.new('RGB', (4000, 3000), 'white').save(source, format='JPEG', quality=95)
        upload = SimpleUploadedFile('large.jpg', source.getvalue(), content_type='image/jpeg')

        optimized = _compress(upload)

        self.assertTrue(optimized.name.endswith('.webp'))
        optimized.seek(0)
        with Image.open(optimized) as image:
            self.assertLessEqual(max(image.size), 1920)
            self.assertEqual(image.format, 'WEBP')

    def test_invalid_image_is_rejected(self):
        upload = SimpleUploadedFile('bad.jpg', b'not-an-image', content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            _compress(upload)

from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_PER_ZONE = 5
MAX_TOTAL = 40
MAX_DIMENSION = 1600
WEBP_QUALITY = 74
MAX_IMAGE_BYTES = 1_000_000


def _compress(uploaded):
    """Validate one image and recompress it to a bounded WebP when needed."""
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as source:
            source.verify()
        uploaded.seek(0)
        with Image.open(uploaded) as source:
            width, height = source.size
            if (uploaded.size <= MAX_IMAGE_BYTES and source.format == 'WEBP'
                    and max(width, height) <= MAX_DIMENSION):
                uploaded.seek(0)
                return uploaded
            image = ImageOps.exif_transpose(source).convert('RGB')
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format='WEBP', quality=WEBP_QUALITY, method=4)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError('Une des photos sélectionnées est invalide ou illisible.') from exc

    name = uploaded.name.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
    stem = name.rsplit('.', 1)[0] or 'photo'
    return ContentFile(output.getvalue(), name=f'{stem}.webp')


def save_photos(prop, request, post):
    """Save up to five photos per zone and forty photos per property."""
    from . import views
    uploads_by_slot = []
    total_new = 0
    for slot_key, label, category, room_number in views._photo_slots(post):
        files = request.FILES.getlist(f'photos_{slot_key}')
        if len(files) > MAX_PER_ZONE:
            raise ValidationError(f'{label} : maximum {MAX_PER_ZONE} photos.')
        if files:
            uploads_by_slot.append((label, category, room_number, files))
            total_new += len(files)
    if not total_new:
        return
    existing_total = prop.photos.count()
    if existing_total + total_new > MAX_TOTAL:
        raise ValidationError(f'Maximum {MAX_TOTAL} photos par logement.')
    for label, category, room_number, files in uploads_by_slot:
        existing_slot = prop.photos.filter(category=category, order=room_number).count()
        if existing_slot + len(files) > MAX_PER_ZONE:
            raise ValidationError(f'{label} : il reste seulement {MAX_PER_ZONE - existing_slot} emplacement(s) photo.')
        for image in files:
            optimized = _compress(image)
            prop.photos.create(image=optimized, category=category, order=room_number, is_primary=(existing_total == 0))
            existing_total += 1


def install():
    """Install the photo policy in the existing publication workflow."""
    from . import views
    views.PHOTO_MAX_PER_ROOM = MAX_PER_ZONE
    views.PHOTO_MAX_TOTAL = MAX_TOTAL
    views._save_photos = save_photos

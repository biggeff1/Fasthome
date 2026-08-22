from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_PER_ZONE = 1
MAX_TOTAL = 50
MAX_DIMENSION = 1920
WEBP_QUALITY = 82


def _compress(uploaded):
    """Validate and compress one uploaded image before it reaches storage."""
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as source:
            source.verify()
        uploaded.seek(0)
        with Image.open(uploaded) as source:
            image = ImageOps.exif_transpose(source).convert('RGB')
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format='WEBP', quality=WEBP_QUALITY, method=6)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError('Une des photos sélectionnées est invalide ou illisible.') from exc

    name = uploaded.name.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
    stem = name.rsplit('.', 1)[0] or 'photo'
    return ContentFile(output.getvalue(), name=f'{stem}.webp')


def save_photos(prop, request, post):
    """Save one optimized photo per declared zone, up to 50 per property."""
    from . import views

    uploads_by_slot = []
    total_new = 0
    for slot_key, label, category, room_number in views._photo_slots(post):
        files = request.FILES.getlist(f'photos_{slot_key}')
        if len(files) > MAX_PER_ZONE:
            raise ValidationError(f'{label} : maximum {MAX_PER_ZONE} photo.')
        if files:
            uploads_by_slot.append((label, category, room_number, files[0]))
            total_new += 1

    if not total_new:
        return

    existing_total = prop.photos.count()
    if existing_total + total_new > MAX_TOTAL:
        raise ValidationError(f'Maximum {MAX_TOTAL} photos par logement.')

    for label, category, room_number, image in uploads_by_slot:
        existing_slot = prop.photos.filter(category=category, order=room_number).exists()
        if existing_slot:
            raise ValidationError(f'{label} : cette zone possède déjà une photo.')
        optimized = _compress(image)
        prop.photos.create(
            image=optimized,
            category=category,
            order=room_number,
            is_primary=(existing_total == 0),
        )
        existing_total += 1


def install():
    """Install the photo policy in the existing publication workflow."""
    from . import views

    views.PHOTO_MAX_PER_ROOM = MAX_PER_ZONE
    views.PHOTO_MAX_TOTAL = MAX_TOTAL
    views._save_photos = save_photos

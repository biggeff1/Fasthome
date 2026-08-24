from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def validate_file_size(uploaded_file, max_bytes: int, label: str = 'Fichier') -> None:
    size = getattr(uploaded_file, 'size', None)
    if size is None:
        raise ValidationError(f'{label} invalide.')
    if size > max_bytes:
        raise ValidationError(f'{label} trop volumineux. Taille maximale : {max_bytes // (1024 * 1024)} Mo.')


def validate_image_upload(uploaded_file) -> None:
    validate_file_size(uploaded_file, MAX_IMAGE_SIZE, 'Image')
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError('Format d’image non autorisé. Utilisez JPG, JPEG, PNG ou WebP.')
    try:
        from PIL import Image
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image.verify()
        uploaded_file.seek(0)
    except Exception as exc:
        raise ValidationError('Le fichier image est illisible ou invalide.') from exc


def validate_identity_document(uploaded_file) -> None:
    validate_file_size(uploaded_file, MAX_DOCUMENT_SIZE, 'Document')
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError('Format de document non autorisé. Utilisez PDF, JPG, JPEG ou PNG.')
    if suffix == '.pdf':
        uploaded_file.seek(0)
        header = uploaded_file.read(5)
        uploaded_file.seek(0)
        if header != b'%PDF-':
            raise ValidationError('Le fichier PDF est invalide.')
    else:
        validate_image_upload(uploaded_file)


image_extension_validator = FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])

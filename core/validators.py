from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


def validate_file_size(uploaded_file, max_bytes: int, label: str = 'Fichier') -> None:
    size = getattr(uploaded_file, 'size', None)
    if size is None:
        raise ValidationError(f'{label} invalide.')
    if size > max_bytes:
        raise ValidationError(f'{label} trop volumineux. Taille maximale : {max_bytes // (1024 * 1024)} Mo.')


def validate_image_upload(uploaded_file) -> None:
    validate_file_size(uploaded_file, MAX_IMAGE_SIZE, 'Image')


def validate_identity_document(uploaded_file) -> None:
    validate_file_size(uploaded_file, MAX_DOCUMENT_SIZE, 'Document')
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {'.pdf', '.jpg', '.jpeg', '.png'}:
        raise ValidationError('Format de document non autorisé. Utilisez PDF, JPG, JPEG ou PNG.')


image_extension_validator = FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])

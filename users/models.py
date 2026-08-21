import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from core.validators import validate_identity_document, validate_image_upload


def make_code(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:10].upper()}'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, unique=True)
    last_name = models.CharField(max_length=100)
    postname = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100)
    birth_date = models.DateField(null=True, blank=True)
    SEX_CHOICES = [('M', 'Homme'), ('F', 'Femme')]
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True)
    profession = models.CharField(max_length=160, blank=True)
    fasthome_id = models.CharField(max_length=32, unique=True, editable=False)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_certified = models.BooleanField(default=False)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True, validators=[validate_image_upload])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone', 'last_name', 'first_name']

    def save(self, *args, **kwargs):
        if not self.fasthome_id:
            self.fasthome_id = make_code('FH')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_full_name()} ({self.fasthome_id})'


class IdentityVerification(models.Model):
    DOCUMENT_TYPES = [('PASSPORT', 'Passeport'), ('VOTER_CARD', "Carte d'électeur"), ('DRIVING_LICENSE', 'Permis de conduire')]
    STATUS = [('PENDING', 'En attente'), ('IN_REVIEW', 'En vérification'), ('VERIFIED', 'Vérifiée'), ('REJECTED', 'Refusée'), ('RETRY', 'À refaire')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='identity_verification')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='private/identity/', validators=[validate_identity_document])
    facial_status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    def clean(self):
        super().clean()
        if self.facial_status == 'VERIFIED' and self.status != 'VERIFIED':
            raise ValidationError({'status': 'La vérification faciale ne peut être finale avant la validation du document.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        certified = self.status == 'VERIFIED' and self.facial_status == 'VERIFIED'
        if self.user.is_certified != certified:
            type(self.user).objects.filter(pk=self.user_id).update(is_certified=certified)

    def __str__(self):
        return f'{self.user.fasthome_id} - {self.status}'

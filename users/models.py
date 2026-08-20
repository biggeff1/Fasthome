import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


def make_code(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:10].upper()}'


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
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    document_file = models.FileField(upload_to='private/identity/')
    facial_status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return f'{self.user.fasthome_id} - {self.status}'

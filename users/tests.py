from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import IdentityVerification, User


class UserSecurityTests(TestCase):
    def test_fasthome_id_is_generated_and_unique(self):
        first = User.objects.create_user(email='one@example.com', password='A-secure-password-123', phone='+243900000001', last_name='A', first_name='One')
        second = User.objects.create_user(email='two@example.com', password='A-secure-password-123', phone='+243900000002', last_name='B', first_name='Two')
        self.assertTrue(first.fasthome_id.startswith('FH-'))
        self.assertNotEqual(first.fasthome_id, second.fasthome_id)

    def test_certification_requires_both_document_and_face(self):
        user = User.objects.create_user(email='cert@example.com', password='A-secure-password-123', phone='+243900000003', last_name='Cert', first_name='Test')
        verification = IdentityVerification(
            user=user,
            document_type='PASSPORT',
            document_file=SimpleUploadedFile('passport.pdf', b'%PDF-1.4 test', content_type='application/pdf'),
            status='VERIFIED',
            facial_status='PENDING',
        )
        with self.assertRaises(ValidationError):
            verification.full_clean()

    def test_user_is_certified_only_after_both_checks(self):
        user = User.objects.create_user(email='cert2@example.com', password='A-secure-password-123', phone='+243900000004', last_name='Cert', first_name='Two')
        verification = IdentityVerification(
            user=user,
            document_type='PASSPORT',
            document_file=SimpleUploadedFile('passport.pdf', b'%PDF-1.4 test', content_type='application/pdf'),
            status='VERIFIED',
            facial_status='VERIFIED',
        )
        verification.save()
        user.refresh_from_db()
        self.assertTrue(user.is_certified)

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import IdentityVerification, User


class UserSecurityTests(TestCase):
    def make_user(self, email, phone):
        return User.objects.create_user(
            email=email,
            password='A-secure-password-123',
            phone=phone,
            last_name='Test',
            first_name='User',
        )

    def test_fasthome_id_is_generated_and_unique(self):
        first = self.make_user('one@example.com', '+243900000001')
        second = self.make_user('two@example.com', '+243900000002')
        self.assertTrue(first.fasthome_id.startswith('FH-'))
        self.assertNotEqual(first.fasthome_id, second.fasthome_id)

    def test_certification_requires_both_document_and_face(self):
        user = self.make_user('cert@example.com', '+243900000003')
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
        user = self.make_user('cert2@example.com', '+243900000004')
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

    def test_user_manager_rejects_empty_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='', password='A-secure-password-123', phone='+243900000005',
                last_name='Test', first_name='User'
            )

    def test_superuser_manager_sets_required_flags(self):
        admin = User.objects.create_superuser(
            email='admin@example.com', password='A-secure-password-123',
            phone='+243900000006', last_name='Admin', first_name='User'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

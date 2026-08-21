from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from users.models import IdentityVerification, User


class VerificationModerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='kyc-user@example.com',
            password='A-secure-password-123',
            phone='+243900009101',
            last_name='KYC',
            first_name='User',
        )
        self.staff = User.objects.create_user(
            email='kyc-staff@example.com',
            password='A-secure-password-123',
            phone='+243900009102',
            last_name='KYC',
            first_name='Staff',
            is_staff=True,
        )
        self.verification = IdentityVerification.objects.create(
            user=self.user,
            document_type='PASSPORT',
            document_file=SimpleUploadedFile('identity.pdf', b'%PDF-1.4 test'),
        )

    def test_document_then_face_makes_user_certified(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_document'})
        self.verification.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.verification.status, 'VERIFIED')
        self.assertFalse(self.user.is_certified)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_face'})
        self.verification.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.verification.facial_status, 'VERIFIED')
        self.assertTrue(self.user.is_certified)

    def test_face_cannot_be_finalized_before_document(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_face'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, 'PENDING')
        self.assertEqual(self.verification.facial_status, 'PENDING')

    def test_rejection_requires_reason_and_revokes_certification(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_document'})
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_face'})
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_certified)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'reject', 'reason': 'Document illisible.'})
        self.verification.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.verification.status, 'RETRY')
        self.assertEqual(self.verification.facial_status, 'RETRY')
        self.assertFalse(self.user.is_certified)

    def test_non_staff_cannot_moderate_kyc(self):
        self.client.force_login(self.user)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_document'}, follow=True)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, 'PENDING')

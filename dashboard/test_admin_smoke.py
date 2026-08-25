from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminSmokeTests(TestCase):
    """Ensure every registered admin changelist renders without a 500."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin_user = User.objects.create_superuser(
            email='admin-smoke@example.test',
            password='AdminSmokePass123!',
            phone='+243000000001',
            last_name='Admin',
            first_name='Smoke',
        )

    def test_all_registered_changelists_render(self):
        self.client.force_login(self.admin_user)
        failures = []

        for model in admin.site._registry:
            opts = model._meta
            url_name = f'admin:{opts.app_label}_{opts.model_name}_changelist'
            try:
                response = self.client.get(reverse(url_name))
            except Exception as exc:  # noqa: BLE001 - expose the failing route
                failures.append(f'{url_name}: {type(exc).__name__}: {exc}')
                continue
            if response.status_code >= 500:
                failures.append(f'{url_name}: HTTP {response.status_code}')

        self.assertFalse(
            failures,
            'Admin changelist failures:\n' + '\n'.join(failures),
        )

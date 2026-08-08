from django.test import TestCase
from rest_framework.test import APIClient
from .models import Suggestion
from users.models import User


class SuggestionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@test.com", name="مستخدم", password="123456")

    def test_create_suggestion_default_status_pending(self):
        s = Suggestion.objects.create(
            type='add', target_type='product',
            data_json={'name': 'منتج مقترح'}, user=self.user
        )
        self.assertEqual(s.status, 'pending')
        self.assertIn('add', str(s))


class SuggestionWhiteBoxTest(TestCase):
    """تغطية: POST يتطلب تسجيل دخول فقط / GET+PATCH يتطلب صلاحية مشرف"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="u2@test.com", name="مستخدم", password="123456")
        self.admin = User.objects.create_superuser(
            email="admin_sug@test.com", name="مشرف", password="123456"
        )

    def test_create_suggestion_requires_login(self):
        response = self.client.post('/api/suggestions/', {
            'type': 'add', 'target_type': 'product', 'data_json': {'name': 'اقتراح'}
        }, format='json')
        self.assertEqual(response.status_code, 401)

    def test_create_suggestion_authenticated_user_succeeds(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/suggestions/', {
            'type': 'add', 'target_type': 'product', 'data_json': {'name': 'اقتراح'}
        }, format='json')
        self.assertEqual(response.status_code, 201)

    def test_list_suggestions_requires_admin(self):
        """مستخدم عادي (غير مشرف) لا يقدر يشوف كل الاقتراحات"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/suggestions/')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_approve_suggestion(self):
        suggestion = Suggestion.objects.create(
            type='add', target_type='product', data_json={'name': 'اقتراح'}, user=self.user
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/suggestions/{suggestion.id}/', {'status': 'approved'}, format='json')
        self.assertEqual(response.status_code, 200)
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, 'approved')

    def test_suggestion_not_found_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/suggestions/9999/')
        self.assertEqual(response.status_code, 404)
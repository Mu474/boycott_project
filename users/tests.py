from django.test import TestCase
from rest_framework.test import APIClient
from .models import User


class UserModelTest(TestCase):
    def test_create_user(self):
        u = User.objects.create_user(email="a@test.com", name="أحمد", password="123456")
        self.assertTrue(u.check_password("123456"))
        self.assertFalse(u.is_staff)

    def test_create_superuser(self):
        u = User.objects.create_superuser(email="admin@test.com", name="مشرف", password="123456")
        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_superuser)

    def test_create_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", name="بدون بريد", password="123456")


class AuthWhiteBoxTest(TestCase):
    """تغطية فرعَي نجاح/فشل تسجيل الدخول في LoginView"""

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(email="test@test.com", name="مستخدم", password="pass123")

    def test_login_success_branch(self):
        res = self.client.post('/api/auth/login/', {'email': 'test@test.com', 'password': 'pass123'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)

    def test_login_failure_branch(self):
        res = self.client.post('/api/auth/login/', {'email': 'test@test.com', 'password': 'wrong'})
        self.assertEqual(res.status_code, 401)

    def test_register_short_password_rejected(self):
        res = self.client.post('/api/auth/register/', {'email': 'b@test.com', 'name': 'باسم', 'password': '123'})
        self.assertEqual(res.status_code, 400)

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@test.com", name="مستخدم", password="123456")
        res = self.client.post('/api/auth/register/', {
            'email': 'dup@test.com', 'name': 'آخر', 'password': '123456'
        })
        self.assertEqual(res.status_code, 400)

    def test_register_success_returns_tokens(self):
        res = self.client.post('/api/auth/register/', {
            'email': 'new@test.com', 'name': 'جديد', 'password': '123456'
        })
        self.assertEqual(res.status_code, 201)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)


class UserPermissionTest(TestCase):
    """يتأكد أن قائمة المستخدمين وحذفهم متاح فقط للمشرف"""

    def setUp(self):
        self.client = APIClient()
        self.regular_user = User.objects.create_user(email="reg@test.com", name="عادي", password="123456")
        self.admin = User.objects.create_superuser(email="admin_u@test.com", name="مشرف", password="123456")

    def test_user_list_requires_admin(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/auth/users/')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_users(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/auth/users/')
        self.assertEqual(response.status_code, 200)

    def test_admin_can_delete_user(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/auth/users/{self.regular_user.id}/')
        self.assertEqual(response.status_code, 204)

    def test_delete_nonexistent_user_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete('/api/auth/users/9999/')
        self.assertEqual(response.status_code, 404)
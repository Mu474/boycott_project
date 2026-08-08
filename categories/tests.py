from django.test import TestCase
from rest_framework.test import APIClient
from .models import Category
from users.models import User
from entities.models import BusinessEntity


class CategoryModelTest(TestCase):
    def test_create_root_category(self):
        cat = Category.objects.create(name="أغذية", icon="🍔")
        self.assertEqual(str(cat), "أغذية")
        self.assertIsNone(cat.parent_category)

    def test_create_subcategory(self):
        parent = Category.objects.create(name="مشروبات")
        child = Category.objects.create(name="غازية", parent_category=parent)
        self.assertEqual(child.parent_category, parent)
        self.assertIn(child, parent.subcategories.all())

    def test_delete_parent_keeps_child(self):
        parent = Category.objects.create(name="ملابس")
        child = Category.objects.create(name="أحذية", parent_category=parent)
        parent.delete()
        child.refresh_from_db()
        self.assertIsNone(child.parent_category)


class CategoryWhiteBoxTest(TestCase):
    """تغطية مسارات CategoryDetailView.delete(): نجاح / ProtectedError"""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin_cat@test.com", name="مشرف", password="123456"
        )
        self.client.force_authenticate(user=self.admin)
        self.category = Category.objects.create(name="أغذية")

    def test_delete_success_path(self):
        response = self.client.delete(f'/api/categories/{self.category.id}/')
        self.assertEqual(response.status_code, 204)

    def test_delete_protected_path(self):
        BusinessEntity.objects.create(
            name="جهة", status="boycott", category=self.category
        )
        response = self.client.delete(f'/api/categories/{self.category.id}/')
        self.assertEqual(response.status_code, 400)

    def test_delete_not_found_path(self):
        response = self.client.delete('/api/categories/9999/')
        self.assertEqual(response.status_code, 404)

    def test_delete_without_auth_returns_401(self):
        anon_client = APIClient()
        response = anon_client.delete(f'/api/categories/{self.category.id}/')
        self.assertEqual(response.status_code, 401)

    def test_get_subcategories(self):
        Category.objects.create(name="فرعي", parent_category=self.category)
        response = self.client.get(f'/api/categories/{self.category.id}/subcategories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
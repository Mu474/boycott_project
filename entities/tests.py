from django.test import TestCase
from rest_framework.test import APIClient
from categories.models import Category
from .models import BusinessEntity
from products.models import Product
from users.models import User


class EntityModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="أغذية")

    def test_create_entity(self):
        e = BusinessEntity.objects.create(name="شركة أ", status="boycott", category=self.category)
        self.assertEqual(str(e), "شركة أ")

    def test_subsidiary_relation(self):
        parent = BusinessEntity.objects.create(name="الشركة الأم", status="boycott", category=self.category)
        sub = BusinessEntity.objects.create(
            name="علامة تابعة", status="boycott", category=self.category, parent_entity=parent
        )
        self.assertIn(sub, parent.subsidiaries.all())

    def test_delete_parent_sets_null(self):
        parent = BusinessEntity.objects.create(name="أم", status="boycott", category=self.category)
        sub = BusinessEntity.objects.create(
            name="فرع", status="boycott", category=self.category, parent_entity=parent
        )
        parent.delete()
        sub.refresh_from_db()
        self.assertIsNone(sub.parent_entity)


class EntityDeleteWhiteBoxTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin_entity@test.com", name="مشرف", password="123456"
        )
        self.client.force_authenticate(user=self.admin)
        self.category = Category.objects.create(name="أغذية")
        self.entity = BusinessEntity.objects.create(
            name="شركة تجريبية", status="boycott", category=self.category
        )

    def test_delete_success_path(self):
        response = self.client.delete(f'/api/entities/{self.entity.id}/')
        self.assertEqual(response.status_code, 204)

    def test_delete_protected_path(self):
        Product.objects.create(
            name="منتج", barcode="1111", status="boycott",
            category=self.category, entity=self.entity
        )
        response = self.client.delete(f'/api/entities/{self.entity.id}/')
        self.assertEqual(response.status_code, 400)


class EntityDeletePermissionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="أغذية")
        self.entity = BusinessEntity.objects.create(
            name="شركة", status="boycott", category=self.category
        )

    def test_delete_without_auth_returns_401(self):
        response = self.client.delete(f'/api/entities/{self.entity.id}/')
        self.assertEqual(response.status_code, 401)


class EntityRelatedEndpointsTest(TestCase):
    """اختبار endpoints الإضافية: subsidiaries, products, alternatives, top-boycotted"""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="أغذية")
        self.parent = BusinessEntity.objects.create(name="أم", status="boycott", category=self.category)
        self.sub = BusinessEntity.objects.create(
            name="فرع", status="boycott", category=self.category, parent_entity=self.parent
        )
        self.alt_entity = BusinessEntity.objects.create(name="بديل", status="alternative", category=self.category)
        Product.objects.create(name="منتج1", barcode="p1", status="boycott",
                                category=self.category, entity=self.parent)

    def test_subsidiaries_endpoint(self):
        response = self.client.get(f'/api/entities/{self.parent.id}/subsidiaries/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_products_endpoint(self):
        response = self.client.get(f'/api/entities/{self.parent.id}/products/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_alternatives_exclude_self_and_match_category(self):
        response = self.client.get(f'/api/entities/{self.parent.id}/alternatives/')
        names = [e['name'] for e in response.data]
        self.assertIn('بديل', names)
        self.assertNotIn('أم', names)

    def test_top_boycotted_endpoint(self):
        response = self.client.get('/api/entities/top-boycotted/')
        self.assertEqual(response.status_code, 200)
        ids = [e['id'] for e in response.data]
        self.assertIn(self.parent.id, ids)

    def test_entity_not_found_returns_404(self):
        response = self.client.get('/api/entities/9999/products/')
        self.assertEqual(response.status_code, 404)
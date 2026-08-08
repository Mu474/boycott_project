from django.test import TestCase
from rest_framework.test import APIClient
from categories.models import Category
from entities.models import BusinessEntity
from .models import Product
from users.models import User


class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="أغذية")
        self.entity = BusinessEntity.objects.create(name="شركة", status="boycott", category=self.category)

    def test_create_product(self):
        p = Product.objects.create(
            name="منتج 1", barcode="123", status="boycott",
            category=self.category, entity=self.entity
        )
        self.assertEqual(str(p), "منتج 1")

    def test_duplicate_barcode_raises_error(self):
        Product.objects.create(
            name="أ", barcode="999", status="boycott",
            category=self.category, entity=self.entity
        )
        with self.assertRaises(Exception):
            Product.objects.create(
                name="ب", barcode="999", status="boycott",
                category=self.category, entity=self.entity
            )


class ProductWhiteBoxTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin_product@test.com", name="مشرف", password="123456"
        )
        self.client.force_authenticate(user=self.admin)
        self.category = Category.objects.create(name="أغذية")
        self.entity = BusinessEntity.objects.create(name="ش", status="boycott", category=self.category)
        Product.objects.create(
            name="بيبسي", barcode="111", status="boycott",
            category=self.category, entity=self.entity
        )
        Product.objects.create(
            name="بديل محلي", barcode="222", status="alternative",
            category=self.category, entity=self.entity
        )

    def test_valid_status_filter_branch(self):
        res = self.client.get('/api/products/?status=boycott')
        self.assertEqual(len(res.data), 1)

    def test_invalid_status_filter_ignored(self):
        res = self.client.get('/api/products/?status=xxx')
        self.assertEqual(len(res.data), 2)

    def test_search_by_name_or_barcode(self):
        res = self.client.get('/api/products/?search=222')
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], 'بديل محلي')

    def test_alternatives_exclude_self(self):
        alt_product = Product.objects.get(barcode="222")
        res = self.client.get(f'/api/products/{alt_product.id}/alternatives/')
        ids = [p['id'] for p in res.data]
        self.assertNotIn(alt_product.id, ids)

    def test_product_not_found_returns_404(self):
        res = self.client.get('/api/products/9999/')
        self.assertEqual(res.status_code, 404)

    def test_delete_product_success(self):
        product = Product.objects.get(barcode="111")
        response = self.client.delete(f'/api/products/{product.id}/')
        self.assertEqual(response.status_code, 204)


class ProductBarcodeSearchTest(TestCase):
    """اختبار مسح الباركود والبحث اليدوي - وظائف أساسية بالمشروع"""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="أغذية")
        self.entity = BusinessEntity.objects.create(name="ش", status="boycott", category=self.category)
        Product.objects.create(name="شوكولاتة", barcode="7771", status="boycott",
                                category=self.category, entity=self.entity)

    def test_barcode_found(self):
        response = self.client.get('/api/products/barcode/7771/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'شوكولاتة')

    def test_barcode_not_found(self):
        response = self.client.get('/api/products/barcode/0000/')
        self.assertEqual(response.status_code, 404)

    def test_search_with_query(self):
        response = self.client.get('/api/products/search/?q=شوكو')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_search_without_query_returns_400(self):
        response = self.client.get('/api/products/search/')
        self.assertEqual(response.status_code, 400)

    def test_random_alternatives_only_returns_alternative_status(self):
        Product.objects.create(name="بديل", barcode="8881", status="alternative",
                                category=self.category, entity=self.entity)
        response = self.client.get('/api/products/alternatives/random/')
        statuses = set(p['status'] for p in response.data)
        self.assertTrue(statuses.issubset({'alternative'}))


class ProductPermissionTest(TestCase):
    """يتأكد أن غير المصادَق عليه لا يقدر يضيف/يعدل/يحذف منتجات"""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="أغذية")
        self.entity = BusinessEntity.objects.create(name="ش", status="boycott", category=self.category)

    def test_create_without_auth_returns_401(self):
        response = self.client.post('/api/products/', {
            'name': 'منتج', 'barcode': '555', 'status': 'boycott',
            'category': self.category.id, 'entity': self.entity.id, 'reason': 'سبب'
        })
        self.assertEqual(response.status_code, 401)

    def test_get_products_without_auth_allowed(self):
        """القراءة (GET) مسموحة للجميع - AllowAny"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)